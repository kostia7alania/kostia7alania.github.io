#!/usr/bin/env python3
import argparse
from contextlib import closing
import hmac
from http.client import HTTPConnection, HTTPSConnection, HTTPException
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
from urllib.parse import urlsplit
import uuid


BATCH_SIZE = 32
MAX_EVENT = 32 * 1024
MAX_BODY = BATCH_SIZE * MAX_EVENT + 4096
MAX_ID = 2**63 - 1
SERVER_DB = 0x41595553
CLIENT_DB = 0x41595543
FIELDS = {
    'event_id', 'source', 'kind', 'account_id', 'dialog_id', 'message_id',
    'text', 'message_date', 'edit_date', 'observed_at',
}


class ConflictError(ValueError):
    pass


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def valid_id(value):
    return isinstance(value, str) and re.fullmatch(r'[1-9][0-9]{0,18}', value) and int(value) <= MAX_ID


def valid_source(value):
    return isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}', value)


def event_payload(event):
    if not isinstance(event, dict) or event.keys() != FIELDS:
        raise ValueError('invalid event fields')
    event_id = event['event_id']
    if not isinstance(event_id, str) or not re.fullmatch(r'[a-f0-9]{64}', event_id):
        raise ValueError('invalid event ID')
    if not valid_source(event['source']):
        raise ValueError('invalid source name')
    if event['kind'] not in ('edited_snapshot', 'deleted_snapshot'):
        raise ValueError('unsupported event kind')
    if any(not valid_id(event[field]) for field in ('account_id', 'dialog_id', 'message_id')):
        raise ValueError('invalid Telegram ID')
    for field in ('message_date', 'edit_date', 'observed_at'):
        if type(event[field]) is not int or not 0 <= event[field] <= MAX_ID:
            raise ValueError(f'invalid {field}')
    if not isinstance(event['text'], str):
        raise ValueError('event text must be a string')
    payload = encode(event)
    if len(payload) > MAX_EVENT:
        raise ValueError('event exceeds size limit')
    return payload


def open_archive(path, role, *, create=False, writable=False):
    path = path.resolve()
    if create:
        try:
            os.close(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600))
        except FileExistsError:
            pass
    mode = 'rw' if create or writable else 'ro'
    db = sqlite3.connect(f'{path.as_uri()}?mode={mode}', uri=True, timeout=10)
    try:
        if create:
            db.execute('BEGIN IMMEDIATE')
        application_id = db.execute('PRAGMA application_id').fetchone()[0]
        if create and application_id == 0 and not db.execute('SELECT 1 FROM sqlite_master').fetchone():
            db.execute(f'PRAGMA application_id = {role}')
            db.execute('PRAGMA user_version = 1')
            db.execute('CREATE TABLE archive (id TEXT PRIMARY KEY)')
            db.execute('''CREATE TABLE events (
                seq INTEGER PRIMARY KEY, event_id TEXT NOT NULL UNIQUE,
                account_id TEXT NOT NULL, dialog_id TEXT NOT NULL, payload BLOB NOT NULL
            )''')
            db.execute('CREATE INDEX events_by_dialog ON events (account_id, dialog_id, seq)')
            if role == SERVER_DB:
                db.execute('INSERT INTO archive VALUES (?)', (uuid.uuid4().hex,))
        elif application_id != role or db.execute('PRAGMA user_version').fetchone()[0] != 1:
            raise ValueError('expected a separate v1 sync archive for this command')
        db.commit()
        return db
    except BaseException:
        db.close()
        raise


def archive_id(db):
    row = db.execute('SELECT id FROM archive').fetchone()
    return row[0] if row else None


def position(db):
    row = db.execute('SELECT seq, event_id FROM events ORDER BY seq DESC LIMIT 1').fetchone()
    return archive_id(db), *(row or (0, None))


def event_row(event, payload):
    return event['event_id'], event['account_id'], event['dialog_id'], payload


class SyncHandler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(20)

    def log_message(self, format, *args):
        pass

    def respond(self, status, data):
        payload = encode(data)
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def authorized(self):
        header = self.headers.get('Authorization', '').encode('utf-8')
        if hmac.compare_digest(header, self.server.authorization):
            return True
        self.respond(401, {'error': 'authorization required'})
        return False

    def do_POST(self):
        if not self.authorized():
            return
        if self.path != '/v1/events':
            self.respond(404, {'error': 'route not found'})
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= MAX_BODY:
                raise ValueError('invalid request size')
            events = json.loads(self.rfile.read(length))
            if not isinstance(events, list) or not 0 < len(events) <= BATCH_SIZE:
                raise ValueError('invalid batch size')
            rows = [event_row(event, event_payload(event)) for event in events]
            with closing(open_archive(self.server.path, SERVER_DB, writable=True)) as db, db:
                db.execute('BEGIN IMMEDIATE')
                for event_id, account, dialog, payload in rows:
                    existing = db.execute('SELECT payload FROM events WHERE event_id = ?', (event_id,)).fetchone()
                    if existing:
                        if existing[0] != payload:
                            raise ConflictError('event ID already exists with different data')
                    else:
                        db.execute(
                            'INSERT INTO events (event_id, account_id, dialog_id, payload) VALUES (?, ?, ?, ?)',
                            (event_id, account, dialog, payload),
                        )
        except ConflictError as exc:
            self.respond(409, {'error': str(exc)})
            return
        except (ValueError, RecursionError):
            self.respond(400, {'error': 'invalid event batch'})
            return
        except sqlite3.Error:
            self.respond(503, {'error': 'archive write failed, retry the batch'})
            return
        self.respond(200, {'accepted': len(rows)})

    def do_GET(self):
        if not self.authorized():
            return
        match = re.fullmatch(r'/v1/events\?after=([0-9]{1,19})', self.path)
        if not match or int(match[1]) > MAX_ID:
            self.respond(400, {'error': 'expected /v1/events?after=CURSOR'})
            return
        try:
            with closing(open_archive(self.server.path, SERVER_DB)) as db:
                db.execute('BEGIN')
                after = int(match[1])
                anchor = db.execute('SELECT event_id FROM events WHERE seq = ?', (after,)).fetchone()
                rows = db.execute(
                    'SELECT seq, payload FROM events WHERE seq > ? ORDER BY seq LIMIT ?',
                    (after, BATCH_SIZE),
                ).fetchall()
                data = {
                    'archive_id': archive_id(db),
                    'anchor': anchor[0] if anchor else None,
                    'events': [[seq, json.loads(payload)] for seq, payload in rows],
                }
        except (sqlite3.Error, ValueError):
            self.respond(503, {'error': 'archive read failed'})
            return
        self.respond(200, data)


def token():
    value = os.environ.get('AYU_SYNC_TOKEN', '')
    if not re.fullmatch(r'[A-Za-z0-9_-]{32,128}', value):
        raise ValueError('set AYU_SYNC_TOKEN to an independent URL-safe token (32 to 128 characters)')
    return value


def serve(args):
    authorization = ('Bearer ' + token()).encode('ascii')
    path = args.db.resolve()
    with closing(open_archive(path, SERVER_DB, create=True)):
        pass
    with ThreadingHTTPServer(('127.0.0.1', args.port), SyncHandler) as server:
        server.path = path
        server.authorization = authorization
        print(f'http://127.0.0.1:{server.server_port}', flush=True)
        server.serve_forever()


class Remote:
    def __init__(self, url):
        self.authorization = 'Bearer ' + token()
        address = urlsplit(url)
        if (address.scheme not in ('http', 'https') or not address.hostname
                or address.username is not None or address.password is not None
                or address.path not in ('', '/') or address.query or address.fragment):
            raise ValueError('provide a server URL with no path or credentials')
        if address.scheme == 'http' and address.hostname not in ('localhost', '127.0.0.1', '::1'):
            raise ValueError('use HTTPS or a local forwarded port for a remote archive')
        self.host = address.hostname
        self.port = address.port
        self.connection = HTTPSConnection if address.scheme == 'https' else HTTPConnection

    def request(self, method, route, body=None):
        with closing(self.connection(self.host, self.port, timeout=30)) as connection:
            connection.request(method, route, body=body, headers={
                'Authorization': self.authorization,
                'Content-Type': 'application/json',
            })
            response = connection.getresponse()
            if response.status != 200:
                raise ValueError(f'archive returned HTTP {response.status} for {method} {route}')
            raw = response.read(MAX_BODY + 1)
            if len(raw) > MAX_BODY:
                raise ValueError('archive response exceeds size limit')
            return json.loads(raw)


def list_chats(args):
    from ayugram_import import list_dialogs

    print('account_id\tdialog_id\tedited\tdeleted')
    with closing(list_dialogs(args.db, args.account)) as dialogs:
        for row in dialogs:
            print(*row, sep='\t')


def import_desktop(args):
    from ayugram_import import iter_ayugram_events

    if not valid_source(args.source):
        raise ValueError('invalid source name (use letters, digits, dots, underscores or hyphens)')
    remote = Remote(args.url)
    batch = []
    count = 0

    def upload(events):
        result = remote.request('POST', '/v1/events', b'[' + b','.join(events) + b']')
        if result != {'accepted': len(events)}:
            raise ValueError('unexpected archive acknowledgement')
        return len(events)

    with closing(iter_ayugram_events(args.db, args.source, args.account, args.dialog)) as events:
        for event in events:
            batch.append(event_payload(event))
            if len(batch) == BATCH_SIZE:
                count += upload(batch)
                batch.clear()
        if batch:
            count += upload(batch)
    print(f'Accepted snapshots (including previously imported): {count}')


def pull(args):
    remote = Remote(args.url)
    count = 0
    with closing(open_archive(args.db, CLIENT_DB, create=True)) as db:
        while True:
            with db:
                db.execute('BEGIN')
                current = position(db)
            local_id, after, anchor = current
            result = remote.request('GET', f'/v1/events?after={after}')
            if not isinstance(result, dict) or result.keys() != {'archive_id', 'anchor', 'events'}:
                raise ValueError('invalid archive response')
            remote_id, batch = result['archive_id'], result['events']
            if not isinstance(remote_id, str) or not re.fullmatch(r'[a-f0-9]{32}', remote_id):
                raise ValueError('invalid remote archive identity')
            if local_id and local_id != remote_id:
                raise ValueError('this client file belongs to another archive, use a new --db path')
            if result['anchor'] != anchor:
                raise ValueError('server history differs at the last received event, use a new --db path')
            if not isinstance(batch, list) or len(batch) > BATCH_SIZE:
                raise ValueError('invalid archive batch')
            rows = []
            for entry in batch:
                if not isinstance(entry, list) or len(entry) != 2:
                    raise ValueError('invalid archive entry')
                seq, event = entry
                if type(seq) is not int or seq != after + 1 or seq > MAX_ID:
                    raise ValueError('invalid archive cursor')
                rows.append((seq, *event_row(event, event_payload(event))))
                after = seq
            with db:
                db.execute('BEGIN IMMEDIATE')
                if position(db) != current:
                    raise ValueError('client archive changed during pull, retry')
                if local_id is None:
                    db.execute('INSERT INTO archive VALUES (?)', (remote_id,))
                db.executemany('INSERT INTO events VALUES (?, ?, ?, ?, ?)', rows)
            count += len(rows)
            if len(rows) < BATCH_SIZE:
                break
    print(f'New snapshots: {count}')


def history(args):
    with closing(open_archive(args.db, CLIENT_DB)) as db:
        rows = db.execute(
            'SELECT payload FROM events WHERE account_id = ? AND dialog_id = ? ORDER BY seq',
            (str(args.account), str(args.dialog)),
        )
        for (payload,) in rows:
            if args.text:
                event = json.loads(payload)
                label = 'Edit' if event['kind'] == 'edited_snapshot' else 'Deletion'
                # Keep message text from acting as terminal control sequences.
                text = ''.join(
                    ch if ch == '\n' or ch.isprintable() else f'\\u{ord(ch):04x}'
                    for ch in event['text']
                )
                payload = f"{label} #{event['message_id']} ({event['source']})\n{text}\n".encode('utf-8')
            sys.stdout.buffer.write(payload + b'\n')


def telegram_id(value):
    if not valid_id(value):
        raise argparse.ArgumentTypeError('expected a positive Telegram ID')
    return int(value)


def main():
    parser = argparse.ArgumentParser(description='Sync text snapshots from an AyuGram Desktop backup')
    commands = parser.add_subparsers(dest='command', required=True)
    for name, run in (
        ('serve', serve), ('list-chats', list_chats), ('import-desktop', import_desktop),
        ('pull', pull), ('history', history),
    ):
        command = commands.add_parser(name)
        command.add_argument('--db', type=Path, required=True)
        command.set_defaults(run=run)
        if name in ('import-desktop', 'pull'):
            command.add_argument('--url', required=True)
        if name in ('import-desktop', 'history'):
            command.add_argument('--account', type=telegram_id, required=True)
            command.add_argument('--dialog', type=telegram_id, required=True)
        if name == 'list-chats':
            command.add_argument('--account', type=telegram_id)
        if name == 'history':
            command.add_argument('--text', action='store_true', help='show readable text instead of JSON lines')
        if name == 'import-desktop':
            command.add_argument('--source', required=True)
        if name == 'serve':
            command.add_argument('--port', type=int, choices=range(65536), default=8765, metavar='0..65535')
    args = parser.parse_args()
    try:
        args.run(args)
    except KeyboardInterrupt:
        return 130
    except (OSError, ValueError, sqlite3.Error, HTTPException) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
