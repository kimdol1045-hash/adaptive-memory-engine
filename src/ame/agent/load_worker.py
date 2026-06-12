from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

from ame.agent.load_jobs import mark_load_progress, write_job
from ame.core.corpus import create_corpus
from ame.core.errors import LightRagBackendError, LlmClientError
from ame.core.paths import ensure_runtime_layout
from ame.pipeline import MemoryPipeline


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python -m ame.agent.load_worker <job-json>", file=sys.stderr)
        return 2
    job_path = Path(sys.argv[1])
    job = json.loads(job_path.read_text(encoding="utf-8"))
    job["status"] = "running"
    write_job(job)
    job_id = str(job["job_id"])

    def progress(event: dict) -> None:
        mark_load_progress(job_id, event)

    try:
        ensure_runtime_layout()
        create_corpus(str(job["corpus_id"]))
        report = MemoryPipeline().ingest(
            str(job["corpus_id"]),
            Path(str(job["source_path"])).expanduser(),
            mode=str(job.get("mode") or "llm"),  # type: ignore[arg-type]
            profile=job.get("profile"),
            progress=progress,
        )
    except (LlmClientError, LightRagBackendError, Exception) as exc:
        job = _refresh_job(job_path, job)
        job["status"] = "failed"
        job["error_type"] = type(exc).__name__
        job["error"] = str(exc)
        job["traceback"] = traceback.format_exc()
        write_job(job)
        return 1
    job = _refresh_job(job_path, job)
    job["status"] = "completed"
    job["report"] = report.model_dump(mode="json")
    write_job(job)
    return 0


def _refresh_job(path: Path, fallback: dict) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback


if __name__ == "__main__":
    raise SystemExit(main())
