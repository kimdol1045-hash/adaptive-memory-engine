from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

from ame.agent.load_jobs import write_job
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
    try:
        ensure_runtime_layout()
        create_corpus(str(job["corpus_id"]))
        report = MemoryPipeline().ingest(
            str(job["corpus_id"]),
            Path(str(job["source_path"])).expanduser(),
            mode=str(job.get("mode") or "llm"),  # type: ignore[arg-type]
            profile=job.get("profile"),
        )
    except (LlmClientError, LightRagBackendError, Exception) as exc:
        job["status"] = "failed"
        job["error_type"] = type(exc).__name__
        job["error"] = str(exc)
        job["traceback"] = traceback.format_exc()
        write_job(job)
        return 1
    job["status"] = "completed"
    job["report"] = report.model_dump(mode="json")
    write_job(job)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
