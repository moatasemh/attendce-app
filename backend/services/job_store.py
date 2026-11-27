import threading
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor

JOB_TTL_S = 60 * 60  # تُحذف المهام القديمة بعد ساعة
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="job")
_jobs: dict[str, dict] = {}
_lock = threading.Lock()


def _cleanup() -> None:
    cutoff = time.time() - JOB_TTL_S
    for jid in [j for j, v in _jobs.items() if v["created"] < cutoff]:
        del _jobs[jid]


def _set(job_id: str, **fields) -> None:
    with _lock:
        if job_id in _jobs:
            _jobs[job_id].update(fields)


def _run(job_id: str, fn, args: tuple, kwargs: dict) -> None:
    try:
        result = fn(*args, **kwargs)
        _set(job_id, status="done", result=result)
    except Exception as exc:
        traceback.print_exc()
        _set(job_id, status="error", error=str(exc))


def submit(fn, *args, **kwargs) -> str:
    """מריץ פונקציה ברקע ומחזיר מזהה משימה מיד."""
    job_id = uuid.uuid4().hex
    with _lock:
        _cleanup()
        _jobs[job_id] = {"status": "running", "result": None, "error": None, "created": time.time()}
    _executor.submit(_run, job_id, fn, args, kwargs)
    return job_id


def get(job_id: str) -> dict | None:
    with _lock:
        job = _jobs.get(job_id)
        if job is None:
            return None
        return {"status": job["status"], "result": job["result"], "error": job["error"]}