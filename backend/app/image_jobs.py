"""Persistent metadata and bounded execution for user-triggered image jobs."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from threading import Lock
from uuid import uuid4


class ImageJobNotFound(LookupError):
    pass


class ImageJobConflict(RuntimeError):
    pass


class ImageJobManager:
    def __init__(self, database_path, generate, max_workers=1):
        self.database_path = Path(database_path)
        self.generate = generate
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="dish-image")
        self.lock = Lock()
        self.futures = {}
        self._initialize()

    def _connect(self):
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self):
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS image_jobs (
                    job_id TEXT PRIMARY KEY,
                    recipe_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    result_json TEXT,
                    error TEXT
                )"""
            )
            now = datetime.now(timezone.utc).isoformat()
            connection.execute(
                "UPDATE image_jobs SET status='failed', updated_at=?, error=? WHERE status IN ('queued','running')",
                (now, "The application restarted before this image job completed. Please try again."),
            )

    def _update(self, job_id, status, *, result=None, error=None):
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            connection.execute(
                "UPDATE image_jobs SET status=?, updated_at=?, result_json=?, error=? WHERE job_id=?",
                (status, now, json.dumps(result) if result is not None else None, error, job_id),
            )

    def submit(self, recipe, output_dir):
        job_id = uuid4().hex
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO image_jobs VALUES (?, ?, 'queued', ?, ?, NULL, NULL)",
                (job_id, recipe["recipe_id"], now, now),
            )
        future = self.executor.submit(self._run, job_id, recipe, Path(output_dir))
        with self.lock:
            self.futures[job_id] = future
        future.add_done_callback(lambda _: self._forget(job_id))
        return self.get(job_id)

    def _forget(self, job_id):
        with self.lock:
            self.futures.pop(job_id, None)

    def _run(self, job_id, recipe, output_dir):
        self._update(job_id, "running")
        try:
            result = self.generate(recipe, output_dir)
            self._update(job_id, "completed", result=result)
        except Exception:
            self._update(job_id, "failed", error="Image generation failed or is unavailable. The original recipe remains available.")

    def get(self, job_id):
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM image_jobs WHERE job_id=?", (job_id,)).fetchone()
        if row is None:
            raise ImageJobNotFound(job_id)
        return {
            "job_id": row["job_id"],
            "recipe_id": row["recipe_id"],
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "result": json.loads(row["result_json"]) if row["result_json"] else None,
            "error": row["error"],
        }

    def cancel(self, job_id):
        job = self.get(job_id)
        if job["status"] in ("completed", "failed", "cancelled"):
            raise ImageJobConflict("Only queued image jobs can be cancelled.")
        with self.lock:
            future = self.futures.get(job_id)
        # Future.cancel() can invoke callbacks synchronously; never call it while
        # holding the same lock used by the completion callback.
        cancelled = bool(future and future.cancel())
        if not cancelled:
            raise ImageJobConflict("This image is already generating and cannot be interrupted safely.")
        self._update(job_id, "cancelled", error="Cancelled before image generation started.")
        return self.get(job_id)

    def shutdown(self):
        self.executor.shutdown(wait=True, cancel_futures=False)
