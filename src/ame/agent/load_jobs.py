from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import time
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
        job["status"] = "stale"
        job["process_alive"] = False
        job["error"] = "Load worker process is no longer running, but the job did not write a final status."
        write_job(job)
    elif job.get("status") == "running":
        job["process_alive"] = True
    job["stdout_tail"] = _tail(Path(str(job.get("stdout_path", ""))))
    job["stderr_tail"] = _tail(Path(str(job.get("stderr_path", ""))))
    return job


def mark_load_progress(job_id: str, event: dict[str, Any]) -> dict[str, Any]:
    job = _read_job_file(job_id)
    if job.get("status") in {"starting", "running"}:
        job["status"] = "running"
        job["stage"] = event.get("stage")
        job["progress"] = event
        job["heartbeat_at"] = _now()
        write_job(job)
    return job


def cancel_load_job(job_id: str) -> dict[str, Any]:
    job = _read_job_file(job_id)
    status = str(job.get("status") or "")
    if status in {"completed", "failed", "cancelled", "stale"}:
        job["message"] = f"Job is already {status}."
        return read_load_job(job_id)
    pid = job.get("pid")
    if _pid_running(pid):
        _terminate_pid(int(pid))
    job["status"] = "cancelled"
    job["process_alive"] = False
    job["cancelled_at"] = _now()
    job["message"] = "Load job cancelled. Any staged ingest artifacts were removed."
    cleanup_load_artifacts(corpus_id=str(job.get("corpus_id") or ""), force=True)
    write_job(job)
    return read_load_job(job_id)


def cleanup_load_artifacts(corpus_id: str | None = None, *, include_jobs: bool = False, force: bool = False) -> dict[str, Any]:
    home = ensure_runtime_layout()
    corpora_root = home / "corpora"
    running_corpora = set() if force else _running_corpora()
    removed_dirs: list[str] = []
    skipped_dirs: list[str] = []
    if corpora_root.exists():
        for child in sorted(corpora_root.iterdir()):
            if not child.is_dir() or not child.name.startswith("."):
                continue
            if ".ingest-" not in child.name and ".backup-" not in child.name:
                continue
            parsed = _corpus_from_hidden_artifact(child.name)
            if corpus_id and parsed != corpus_id:
                continue
            if parsed in running_corpora:
                skipped_dirs.append(str(child))
                continue
            shutil.rmtree(child)
            removed_dirs.append(str(child))

    removed_jobs: list[str] = []
    if include_jobs:
        for path in sorted(jobs_root().glob("load-*.json")):
            try:
                job = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if corpus_id and job.get("corpus_id") != corpus_id:
                continue
            if str(job.get("status")) not in {"failed", "stale", "cancelled"}:
                continue
            removed_jobs.append(str(path))
            for key in ["stdout_path", "stderr_path"]:
                log_path = Path(str(job.get(key, "")))
                if log_path.exists():
                    log_path.unlink()
                    removed_jobs.append(str(log_path))
            path.unlink()
    return {
        "ame_home": str(home),
        "corpus_id": corpus_id,
        "removed_staging_dirs": removed_dirs,
        "skipped_running_staging_dirs": skipped_dirs,
        "removed_job_files": removed_jobs,
    }


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


def load_jobs(corpus_id: str | None = None) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(jobs_root().glob("load-*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
        try:
            job = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if corpus_id and job.get("corpus_id") != corpus_id:
            continue
        rows.append(read_load_job(str(job["job_id"])))
    return rows


def job_path(job_id: str) -> Path:
    if "/" in job_id or "\\" in job_id or ".." in job_id:
        raise ValueError("Invalid AME load job id")
    return jobs_root() / f"{job_id}.json"


def _read_job_file(job_id: str) -> dict[str, Any]:
    path = job_path(job_id)
    if not path.exists():
        raise ValueError(f"AME load job does not exist: {job_id}")
    return json.loads(path.read_text(encoding="utf-8"))


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
    if os.name != "nt":
        try:
            result = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True, check=False)
        except OSError:
            return True
        if result.returncode != 0:
            return False
        state = result.stdout.strip()
        if state.startswith("Z"):
            return False
    return True


def _terminate_pid(pid: int) -> None:
    try:
        if os.name != "nt":
            os.killpg(pid, signal.SIGTERM)
        else:
            os.kill(pid, signal.SIGTERM)
    except OSError:
        return
    time.sleep(0.5)
    if not _pid_running(pid):
        return
    try:
        if os.name != "nt":
            os.killpg(pid, signal.SIGKILL)
        else:
            os.kill(pid, signal.SIGTERM)
    except OSError:
        return


def _running_corpora() -> set[str]:
    running = set()
    for path in jobs_root().glob("load-*.json"):
        try:
            job = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if job.get("status") == "running" and _pid_running(job.get("pid")) and job.get("corpus_id"):
            running.add(str(job["corpus_id"]))
    return running


def _corpus_from_hidden_artifact(name: str) -> str:
    if not name.startswith("."):
        return name
    body = name[1:]
    for marker in [".ingest-", ".backup-"]:
        if marker in body:
            return body.split(marker, 1)[0]
    return body
