import sys
import json
import tempfile
from datetime import datetime
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from session_viewer import SessionIndexer, SessionInfo, SessionFilter, ClaudeSessionParser


class SessionIndexerTestCase(unittest.TestCase):
    def test_build_index_and_query(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            session_file = temp_path / "session.jsonl"
            session_file.write_text(
                "\n".join([
                    json.dumps({"type": "user", "message": {"content": "你好 世界"}}),
                    json.dumps({"type": "assistant", "message": {"content": "回复 你好"}}),
                ]),
                encoding="utf-8"
            )

            session = SessionInfo(
                tool="claude",
                session_id="test-session",
                project_path="/Users/zbs/projectwork/demo",
                start_time=datetime(2026, 1, 1, 10, 0),
                last_time=datetime(2026, 1, 1, 10, 1),
                message_count=1,
                first_message="你好 世界",
                file_path=str(session_file),
                file_size=session_file.stat().st_size,
                model="test-model",
                summary="测试总结"
            )

            db_path = temp_path / "index.db"
            indexer = SessionIndexer(db_path, [ClaudeSessionParser()])
            stats = indexer.build_index({"Claude Code": [session]})
            self.assertEqual(stats["indexed"], 1)

            results = indexer.query(SessionFilter(search="回复", project="demo"), tool="claude", limit=None)
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].session_id, "test-session")


if __name__ == "__main__":
    unittest.main()
