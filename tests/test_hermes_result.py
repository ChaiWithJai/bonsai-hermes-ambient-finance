import sqlite3
import tempfile
import unittest
from pathlib import Path
from lib.hermes_result import cursor, final_answer

class HermesResultTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'state.db'
        with sqlite3.connect(self.path) as db:
            db.execute('CREATE TABLE messages(id INTEGER PRIMARY KEY,session_id TEXT,role TEXT,content TEXT,tool_calls TEXT,active INTEGER)')

    def add(self, session, role, content, calls=None):
        with sqlite3.connect(self.path) as db:
            db.execute('INSERT INTO messages(session_id,role,content,tool_calls,active) VALUES(?,?,?,?,1)',(session,role,content,calls))

    def test_reasoning_only_response_is_not_a_draft(self):
        self.add('new','user','Review portfolio')
        self.add('new','assistant','')
        with self.assertRaisesRegex(ValueError,'final answer'):
            final_answer(self.path,0,'Review portfolio')

    def test_reads_new_saved_answer_and_ignores_old_matching_request(self):
        self.add('old','user','Review portfolio')
        self.add('old','assistant','Old draft')
        before=cursor(self.path)
        self.add('new','user','Review portfolio')
        self.add('new','assistant','Saved draft')
        self.assertEqual(final_answer(self.path,before,'Review portfolio'),('new','Saved draft'))

    def test_refuses_ambiguous_sessions(self):
        for name in ('first','second'):
            self.add(name,'user','Review portfolio')
            self.add(name,'assistant','Draft')
        with self.assertRaisesRegex(ValueError,'exactly one'):
            final_answer(self.path,0,'Review portfolio')
