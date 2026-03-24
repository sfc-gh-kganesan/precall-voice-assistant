import json
import os
import sys
import types
from unittest.mock import MagicMock, call

snowflake_mock = types.ModuleType("snowflake")
snowflake_connector_mock = types.ModuleType("snowflake.connector")
snowflake_mock.connector = snowflake_connector_mock
sys.modules["snowflake"] = snowflake_mock
sys.modules["snowflake.connector"] = snowflake_connector_mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".cortex", "skills", "pattern-extract", "stages", "librarian", "scripts"))
from insert_patterns import build_search_content, sync_patterns, insert_patterns_legacy


class TestBuildSearchContent:
    def test_basic(self):
        pattern = {
            "pattern_name": "OAuth Token Refresh",
            "description": "Handles token refresh for long-running jobs.",
            "usage_notes": "Requires requests library.",
            "synthetic_queries": [
                "How do I refresh tokens mid-pipeline?",
                "Token keeps expiring during batch jobs",
            ],
        }
        content = build_search_content(pattern)
        assert "OAuth Token Refresh" in content
        assert "Handles token refresh" in content
        assert "Requires requests library" in content
        assert "How do I refresh tokens mid-pipeline?" in content
        assert "Token keeps expiring" in content

    def test_empty_fields(self):
        pattern = {
            "pattern_name": "Test Pattern",
            "description": "",
            "usage_notes": "",
            "synthetic_queries": [],
        }
        content = build_search_content(pattern)
        assert content == "Test Pattern"

    def test_missing_fields(self):
        pattern = {}
        content = build_search_content(pattern)
        assert content == ""

    def test_no_synthetic_queries(self):
        pattern = {
            "pattern_name": "Simple",
            "description": "A simple pattern.",
        }
        content = build_search_content(pattern)
        assert "Simple" in content
        assert "A simple pattern." in content

    def test_many_queries(self):
        queries = [f"Query {i}" for i in range(10)]
        pattern = {
            "pattern_name": "Multi",
            "description": "Desc",
            "usage_notes": "Notes",
            "synthetic_queries": queries,
        }
        content = build_search_content(pattern)
        for q in queries:
            assert q in content


class TestSyncPatterns:
    def _make_pattern(self, action, pattern_id="test-id", pattern_name="Test Pattern"):
        return {
            "action": action,
            "pattern_id": pattern_id,
            "pattern_name": pattern_name,
            "category": "auth",
            "description": "A test pattern.",
            "abstracted_code": "code here",
            "source_repo_link": "https://github.com/org/repo",
            "repo_name": "repo",
            "complexity_score": 2,
            "dependencies": ["requests"],
            "dependency_graph": {"internal": [], "external": ["requests"]},
            "synthetic_queries": ["How do I test?"],
            "usage_notes": "Use it.",
            "tags": ["auth"],
            "language": "python",
            "framework": "fastapi",
        }

    def test_insert_action(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        patterns = [self._make_pattern("insert", pattern_id="new-id")]
        inserted, updated, deleted = sync_patterns(mock_conn, patterns)

        assert inserted == 1
        assert updated == 0
        assert deleted == 0
        # The INSERT SQL should have been executed
        sql = mock_cursor.execute.call_args_list[0][0][0]
        assert "INSERT INTO" in sql

    def test_update_action(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        patterns = [self._make_pattern("update", pattern_id="existing-id")]
        inserted, updated, deleted = sync_patterns(mock_conn, patterns)

        assert inserted == 0
        assert updated == 1
        assert deleted == 0
        sql = mock_cursor.execute.call_args_list[0][0][0]
        assert "UPDATE" in sql
        assert "UPDATED_AT" in sql
        # pattern_id should be the last parameter (WHERE clause)
        params = mock_cursor.execute.call_args_list[0][0][1]
        assert params[-1] == "existing-id"

    def test_delete_action(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        patterns = [{"action": "delete", "pattern_id": "stale-id", "pattern_name": "Old Pattern"}]
        inserted, updated, deleted = sync_patterns(mock_conn, patterns)

        assert inserted == 0
        assert updated == 0
        assert deleted == 1
        sql = mock_cursor.execute.call_args_list[0][0][0]
        assert "DELETE" in sql
        params = mock_cursor.execute.call_args_list[0][0][1]
        assert params[0] == "stale-id"

    def test_mixed_actions(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        patterns = [
            self._make_pattern("insert", pattern_id="new-1", pattern_name="New"),
            self._make_pattern("update", pattern_id="exist-1", pattern_name="Existing"),
            {"action": "delete", "pattern_id": "stale-1", "pattern_name": "Stale"},
        ]
        inserted, updated, deleted = sync_patterns(mock_conn, patterns)

        assert inserted == 1
        assert updated == 1
        assert deleted == 1
        assert mock_cursor.execute.call_count == 3

    def test_default_action_is_insert(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        patterns = [self._make_pattern("insert", pattern_id="id-1")]
        del patterns[0]["action"]  # No action field
        inserted, updated, deleted = sync_patterns(mock_conn, patterns)

        assert inserted == 1
        assert updated == 0
        assert deleted == 0


class TestInsertPatternsLegacy:
    def test_skips_duplicate(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        # First call (SELECT) returns a row, meaning duplicate
        mock_cursor.fetchone.return_value = ("existing-id",)

        patterns = [{
            "pattern_name": "Dupe",
            "repo_name": "repo",
            "category": "auth",
            "description": "Desc",
            "abstracted_code": "code",
            "source_repo_link": "",
            "complexity_score": 1,
            "dependencies": [],
            "dependency_graph": {},
            "synthetic_queries": [],
            "usage_notes": "",
            "tags": [],
            "language": "python",
            "framework": "",
        }]
        inserted, skipped = insert_patterns_legacy(mock_conn, patterns)

        assert inserted == 0
        assert skipped == 1

    def test_inserts_new(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None  # No duplicate

        patterns = [{
            "pattern_name": "New Pattern",
            "repo_name": "repo",
            "category": "auth",
            "description": "Desc",
            "abstracted_code": "code",
            "source_repo_link": "",
            "complexity_score": 1,
            "dependencies": [],
            "dependency_graph": {},
            "synthetic_queries": [],
            "usage_notes": "",
            "tags": [],
            "language": "python",
            "framework": "",
        }]
        inserted, skipped = insert_patterns_legacy(mock_conn, patterns)

        assert inserted == 1
        assert skipped == 0
        # Should have two execute calls: SELECT check + INSERT
        assert mock_cursor.execute.call_count == 2
