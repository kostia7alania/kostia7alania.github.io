import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import closing, contextmanager
from pathlib import Path


SYNC = Path(__file__).with_name("sync.py")
TOKEN = "roundtrip-test-token-not-used-anywhere-else"


class RoundTripTest(unittest.TestCase):
    def run_client(self, *args, token=TOKEN, check=True):
        result = subprocess.run(
            [sys.executable, "-B", str(SYNC), *map(str, args)],
            env={**os.environ, "AYU_SYNC_TOKEN": token, "PYTHONIOENCODING": "utf-8"},
            capture_output=True,
            encoding="utf-8",
            timeout=15,
        )
        if check:
            self.assertEqual(result.returncode, 0, result.stderr)
        return result

    @contextmanager
    def server(self, db):
        log = db.with_suffix(".test.log")
        with log.open("w", encoding="utf-8") as output:
            process = subprocess.Popen(
                [sys.executable, str(SYNC), "serve", "--db", str(db), "--port", "0"],
                env={**os.environ, "AYU_SYNC_TOKEN": TOKEN},
                stdout=output,
                stderr=subprocess.STDOUT,
            )
        try:
            deadline = time.monotonic() + 10
            while process.poll() is None and time.monotonic() < deadline:
                line, newline, _ = log.read_text(encoding="utf-8").partition("\n")
                if newline and line.startswith("http://127.0.0.1:"):
                    break
                time.sleep(0.05)
            else:
                self.fail(f"Sync server did not start:\n{log.read_text(encoding='utf-8')}")
            yield line
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)

    def history(self, client_db, account=101, dialog=202):
        result = self.run_client("history", "--db", client_db, "--account", account, "--dialog", dialog)
        return [json.loads(line) for line in result.stdout.splitlines()]

    def import_snapshot(self, source_db, url):
        self.run_client(
            "import-desktop", "--db", source_db, "--url", url,
            "--source", "desktop-a", "--account", 101, "--dialog", 202,
        )

    def test_import_restart_retry_and_pull(self):
        with tempfile.TemporaryDirectory(prefix="ayu-sync-test-") as directory:
            root = Path(directory)
            source = root / "ayudata.db"
            server_db = root / "server.db"
            server_backup = root / "server-backup.db"
            client_a = root / "client-a.db"
            client_b = root / "client-b.db"
            with closing(sqlite3.connect(source)) as db, db:
                for table in ("EditedMessage", "DeletedMessage"):
                    db.execute(f"""CREATE TABLE {table} (
                        fakeId INTEGER PRIMARY KEY, userId INTEGER, dialogId INTEGER,
                        messageId INTEGER, date INTEGER, editDate INTEGER,
                        entityCreateDate INTEGER, text TEXT
                    )""")
                db.execute("INSERT INTO EditedMessage VALUES (1, 101, 202, 303, 1000, 0, 1001, 'до правки')")

            original = source.read_bytes()
            with self.server(server_db) as url:
                self.import_snapshot(source, url)
                denied = self.run_client("pull", "--db", client_b, "--url", url, token="x" * 40, check=False)
                self.assertNotEqual(denied.returncode, 0)
                self.run_client("pull", "--db", client_a, "--url", url)
                first = self.history(client_a)
                self.assertEqual([(e["kind"], e["text"]) for e in first], [("edited_snapshot", "до правки")])
            self.assertEqual(source.read_bytes(), original)
            shutil.copyfile(server_db, server_backup)

            with closing(sqlite3.connect(source)) as db, db:
                db.executemany("INSERT INTO DeletedMessage VALUES (?, ?, ?, 303, 1000, 1001, 1002, ?)", [
                    (1, 101, 202, "после правки"),
                    (2, 101, 203, "другой чат"),
                    (3, 102, 202, "другой аккаунт"),
                    (4, 101, -204, "группа"),
                ])
            updated = source.read_bytes()
            catalog = self.run_client("list-chats", "--db", source, "--account", 101)
            self.assertEqual(catalog.stdout.splitlines(), [
                "account_id\tdialog_id\tedited\tdeleted",
                "101\t202\t1\t1",
                "101\t203\t0\t1",
            ])

            with self.server(server_db) as url:
                self.import_snapshot(source, url)
                self.import_snapshot(source, url)
                for client in (client_a, client_b):
                    self.run_client("pull", "--db", client, "--url", url)
                received = self.history(client_a)
                self.assertEqual(received, self.history(client_b))
                self.assertEqual(self.history(client_b, dialog=203), [])
                self.assertEqual(self.history(client_b, account=102), [])
                self.assertEqual(len(received), 2)
                self.assertEqual(received[:1], first)
                deleted = received[1]
                self.assertEqual((deleted["kind"], deleted["text"]), ("deleted_snapshot", "после правки"))
                self.assertEqual((deleted["account_id"], deleted["dialog_id"], deleted["message_id"]), ("101", "202", "303"))
                self.assertEqual((deleted["message_date"], deleted["edit_date"], deleted["observed_at"]), (1000, 1001, 1002))
                self.assertNotEqual(deleted["event_id"], first[0]["event_id"])
                readable = self.run_client(
                    "history", "--db", client_b, "--account", 101, "--dialog", 202, "--text",
                )
                self.assertIn("Deletion #303 (desktop-a)\nпосле правки", readable.stdout)
            self.assertEqual(source.read_bytes(), updated)

            with self.server(server_backup) as url:
                rollback = self.run_client("pull", "--db", client_a, "--url", url, check=False)
                self.assertNotEqual(rollback.returncode, 0)
                self.assertIn("server history differs", rollback.stderr)
                self.assertEqual(self.history(client_a), received)


if __name__ == "__main__":
    unittest.main()
