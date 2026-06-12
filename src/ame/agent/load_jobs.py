from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from ame.core.paths import ame_home, ensure_runtime_layout


def start_load_job(corpus_id: str, source_path: Path, *, mode: str, profile: str | None) -> dict[str, Any]:
    job_id = f"load-{corpus_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:8]}"
    path = job_path(job_id)
    stdout_path = path.with_suffix(".stdout.log")
    stderr_path = path.with_suffix(".stderr.log")
    job = {
        "job_id": job_id,
        "kind": "load",
        "status": "starting",
        "corpus_id": corpus_id,
        "source_path": str(source_path),
        "mode": mode,
        "profile": profile,
        "created_at": _now(),
        "updated_at": _now(),
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
    }
    write_job(job)
    command = [sys.executable, "-m", "ame.agent.load_worker", str(path)]
    env = os.environ.copy()
    env["AME_HOME"] = str(ame_home().expanduser().resolve())
    with stdout_path.open("ab") as stdout, stderr_path.open("ab") as stderr:
        process = subprocess.Popen(command, stdout=stdout, stderr=stderr, env=env, start_new_session=os.name != "nt")
    job.update({"status": "running", "pid": process.pid, "command": command, "updated_at": _now()})
    write_job(job)
    return job


def read_load_job(job_id: str) -> dict[str, Any]:
    path = job_path(job_id)
    if not path.exists():
        raise ValueError(f"AME load job does not exist: {job_id}")
    job = json.loads(path.read_text(encoding="utf-8"))
    if job.get("status") == "running" and not _pid_running(job.get("pid")):
        job["process_alive"] = False
    elif job.get("status") == "running":
        job["process_alive"] = True
    job["stdout_tail"] = _tail(Path(str(job.get("stdout_path", ""))))
    job["stderr_tail"] = _tail(Path(str(job.get("stderr_path", ""))))
    return job


def latest_load_job(corpus_id: str | None = None) -> dict[str, Any] | None:
    candidates = []
    for path in sorted(jobs_root().glob("load-*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
        try:
            job = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if corpus_id and job.get("corpus_id") != corpus_id:
            continue
        candidates.append(job)
    if not candidates:
        return None
    return read_load_job(str(candidates[0]["job_id"]))


def job_path(job_id: str) -> Path:
    if "/" in job_id or "\\" in job_id or ".." in job_id:
        raise ValueError("Invalid AME load job id")
    return jobs_root() / f"{job_id}.json"


def jobs_root() -> Path:
    root = ensure_runtime_layout() / "jobs"
    root.mkdir(parents=True, exist_ok=True)
    try:
        root.chmod(0o700)
    except OSError:
        pass
    return root


def write_job(job: dict[str, Any]) -> None:
    path = job_path(str(job["job_id"]))
    job["updated_at"] = _now()
    tmp_path = path.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(job, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    tmp_path.replace(path)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _tail(path: Path, *, limit: int = 4000) -> str:
    if not path.exists() or not path.is_file():
        return ""
    data = path.read_bytes()
    return data[-limit:].decode("utf-8", errors="replace")


def _pid_running(pid: Any) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True
