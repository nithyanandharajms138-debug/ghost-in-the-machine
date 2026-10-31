import sqlite3
import tempfile
import time
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import Mock, patch

import app


class MemoryQueueTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.queue_path = Path(self.temp_dir.name) / "memory_jobs.sqlite3"
        self.path_patcher = patch.object(app, "MEMORY_QUEUE_PATH", self.queue_path)
        self.path_patcher.start()
        app._initialize_memory_queue()

    def tearDown(self):
        self.path_patcher.stop()
        self.temp_dir.cleanup()

    def test_enqueued_job_is_durable_and_claimable(self):
        job_id = app._enqueue_memory_job("test-user", "Remember this fact.")

        with closing(sqlite3.connect(self.queue_path)) as connection:
            stored_job = connection.execute(
                "SELECT user_id, message, status FROM memory_jobs WHERE id = ?",
                (job_id,),
            ).fetchone()

        claimed_job = app._claim_memory_job()

        self.assertEqual(stored_job, ("test-user", "Remember this fact.", "pending"))
        self.assertEqual(
            claimed_job,
            (job_id, "test-user", "Remember this fact.", 1),
        )

    def test_failed_job_is_retained_for_retry(self):
        job_id = app._enqueue_memory_job("test-user", "Retry this fact.")
        claimed_job = app._claim_memory_job()
        self.assertIsNotNone(claimed_job)

        delay = app._retry_memory_job(job_id, claimed_job[3])

        with closing(sqlite3.connect(self.queue_path)) as connection:
            status, available_at = connection.execute(
                "SELECT status, available_at FROM memory_jobs WHERE id = ?",
                (job_id,),
            ).fetchone()

        self.assertEqual(status, "pending")
        self.assertEqual(delay, 2)
        self.assertGreaterEqual(available_at, time.time())

    def test_expired_claim_is_recovered(self):
        with closing(sqlite3.connect(self.queue_path)) as connection:
            cursor = connection.execute(
                """
                INSERT INTO memory_jobs
                    (user_id, message, status, claimed_pid, lease_until)
                VALUES (?, ?, 'processing', ?, ?)
                """,
                ("test-user", "Recover this fact.", 123, time.time() - 1),
            )
            connection.commit()
            job_id = cursor.lastrowid

        claimed_job = app._claim_memory_job()

        self.assertEqual(
            claimed_job,
            (job_id, "test-user", "Recover this fact.", 1),
        )

    def test_chat_queues_extraction_and_keeps_reply_shape(self):
        ollama_response = Mock()
        ollama_response.json.return_value = {
            "message": {"content": "A whisper returns."}
        }

        with (
            patch.object(app, "_start_memory_worker"),
            patch.object(
                app.memory_store,
                "search",
                return_value={"results": []},
            ) as search,
            patch.object(app.memory_store, "add") as add,
            patch("app.requests.post", return_value=ollama_response),
        ):
            response = app.app.test_client().post(
                "/chat",
                json={"message": "Remember that I like quiet nights."},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"reply": "A whisper returns."})
        self.assertEqual(search.call_args.kwargs["top_k"], 5)
        add.assert_not_called()

        with closing(sqlite3.connect(self.queue_path)) as connection:
            queued_messages = connection.execute(
                "SELECT message FROM memory_jobs"
            ).fetchall()
        self.assertEqual(
            queued_messages,
            [("Remember that I like quiet nights.",)],
        )

    def test_chat_reports_queue_persistence_failure(self):
        with (
            patch.object(app, "_start_memory_worker"),
            patch.object(
                app,
                "_enqueue_memory_job",
                side_effect=sqlite3.OperationalError("disk unavailable"),
            ),
        ):
            response = app.app.test_client().post(
                "/chat",
                json={"message": "Do not lose this message."},
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.get_json(),
            {"reply": "Memory storage is temporarily unavailable. Please try again."},
        )


if __name__ == "__main__":
    unittest.main()
