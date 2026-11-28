"""Read text snapshots from a cold AyuGram Desktop database backup."""

import hashlib
import json
import sqlite3
from contextlib import closing, contextmanager
from pathlib import Path
from typing import Iterator


TABLE_KINDS = {
    "EditedMessage": "edited_snapshot",
    "DeletedMessage": "deleted_snapshot",
}


@contextmanager
def open_backup(path: Path):
    path = path.resolve(strict=True)
    if not path.is_file():
        raise ValueError("Expected an AyuGram Desktop backup file")
    for suffix in ("-wal", "-shm", "-journal"):
        sidecar = path.with_name(path.name + suffix)
        if sidecar.exists() or sidecar.is_symlink():
            raise ValueError(f"Found {suffix} sidecar. Use a cold, standalone SQLite backup")

    # immutable avoids writes beside the input, including WAL shared-memory files.
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)) as database:
        database.execute("PRAGMA trusted_schema = OFF")
        tables = {name for (name,) in database.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        required = {"fakeId", "userId", "dialogId", "messageId", "text", "date"}
        table_columns = {}
        for table in TABLE_KINDS:
            columns = {row[1] for row in database.execute(f"PRAGMA table_info({table})")}
            missing = required - columns
            if table not in tables or missing:
                raise ValueError(f"Unsupported AyuGram Desktop schema for {table}: missing {', '.join(sorted(missing)) or 'table'}")
            table_columns[table] = columns
        yield database, table_columns


def list_dialogs(path: Path, account_id):
    with open_backup(path) as (database, _):
        # Desktop stores groups and channels under negative dialog IDs.
        yield from database.execute("""
            WITH counts AS (
                SELECT userId, dialogId, COUNT(*) AS edits, 0 AS deletions
                FROM EditedMessage
                WHERE typeof(userId) = 'integer' AND userId > 0
                  AND typeof(dialogId) = 'integer' AND dialogId > 0
                  AND (?1 IS NULL OR userId = ?1)
                GROUP BY userId, dialogId
                UNION ALL
                SELECT userId, dialogId, 0, COUNT(*)
                FROM DeletedMessage
                WHERE typeof(userId) = 'integer' AND userId > 0
                  AND typeof(dialogId) = 'integer' AND dialogId > 0
                  AND (?1 IS NULL OR userId = ?1)
                GROUP BY userId, dialogId
            )
            SELECT userId, dialogId, SUM(edits), SUM(deletions)
            FROM counts GROUP BY userId, dialogId ORDER BY userId, dialogId
        """, (account_id,))


def iter_ayugram_events(
    path: Path, source: str, account_id: int, dialog_id: int
) -> Iterator[dict]:
    """Yield old text from one account and one private dialog, in source row order per table."""
    if any(type(value) is not int or not 0 < value < 2**63 for value in (account_id, dialog_id)):
        raise ValueError("account_id and private dialog_id must be positive SQLite integers")
    if not isinstance(source, str) or not source.strip():
        raise ValueError("A nonempty source label is required")

    with open_backup(path) as (database, table_columns):
        for table, columns in table_columns.items():
            edit_date = "COALESCE(editDate, 0)" if "editDate" in columns else "0"
            observed_at = "COALESCE(entityCreateDate, 0)" if "entityCreateDate" in columns else "0"
            query = (
                f"SELECT fakeId, messageId, text, date, {edit_date}, {observed_at} "
                f"FROM {table} WHERE userId = ? AND dialogId = ? ORDER BY fakeId"
            )
            for row in database.execute(query, (account_id, dialog_id)):
                row_id, message_id, text, message_date, edit_date, observed_at = row
                if (any(type(value) is not int or value <= 0 for value in (row_id, message_id))
                        or any(type(value) is not int or value < 0 for value in (message_date, edit_date, observed_at))
                        or not isinstance(text, str)):
                    raise ValueError(f"Invalid row data in {table}")

                event = {
                    "source": source,
                    "account_id": str(account_id),
                    "dialog_id": str(dialog_id),
                    "message_id": str(message_id),
                    "kind": TABLE_KINDS[table],
                    "text": text,
                    "message_date": message_date,
                    "edit_date": edit_date,
                    "observed_at": observed_at,
                }
                # A return to the same text is a distinct revision when it has a different row ID.
                identity = json.dumps(["ayugram-desktop-v1", row_id, event], sort_keys=True)
                event["event_id"] = hashlib.sha256(identity.encode("ascii")).hexdigest()
                yield event
