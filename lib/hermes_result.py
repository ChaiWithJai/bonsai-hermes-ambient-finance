"""Read a new Hermes session's saved answer instead of trusting CLI stdout."""
import sqlite3
from contextlib import closing
from pathlib import Path


def connect(path: Path):
    return sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)


def cursor(path: Path) -> int:
    if not path.exists():
        return 0
    with closing(connect(path)) as db:
        return db.execute('SELECT COALESCE(MAX(id), 0) FROM messages').fetchone()[0]


def final_answer(path: Path, after: int, prompt: str) -> tuple[str, str]:
    if not path.is_file():
        raise ValueError('Hermes session database is missing')
    with closing(connect(path)) as db:
        sessions = db.execute(
            "SELECT DISTINCT session_id FROM messages WHERE id>? AND role='user' AND content=? AND active=1",
            (after, prompt)).fetchall()
        if len(sessions) != 1:
            raise ValueError('Expected exactly one new Hermes session for this request')
        session_id = sessions[0][0]
        row = db.execute(
            'SELECT role, content, tool_calls FROM messages WHERE session_id=? AND active=1 ORDER BY id DESC LIMIT 1',
            (session_id,)).fetchone()
        if not row or row[0] != 'assistant' or not isinstance(row[1], str) or not row[1].strip() or row[2] not in (None, '', '[]'):
            raise ValueError('Hermes did not persist a final answer')
        return session_id, row[1].strip()
