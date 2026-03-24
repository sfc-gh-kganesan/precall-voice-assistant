import json
import os
import sys
import types
from unittest.mock import MagicMock

snowflake_mock = types.ModuleType("snowflake")
snowflake_connector_mock = types.ModuleType("snowflake.connector")
snowflake_mock.connector = snowflake_connector_mock
sys.modules["snowflake"] = snowflake_mock
sys.modules["snowflake.connector"] = snowflake_connector_mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".cortex", "skills", "pattern-extract", "stages", "librarian", "scripts"))
from reconcile_patterns import fetch_existing_patterns, load_fresh_cards


class TestFetchExistingPatterns:
    def test_returns_existing_patterns(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            ("id-1", "OAuth Token Refresh", "Handles token refresh."),
            ("id-2", "Redis Cache Pattern", "Caching with Redis."),
        ]

        result = fetch_existing_patterns(mock_conn, "my-repo")

        mock_cursor.execute.assert_called_once()
        assert len(result) == 2
        assert result[0]["pattern_id"] == "id-1"
        assert result[0]["pattern_name"] == "OAuth Token Refresh"
        assert result[0]["description"] == "Handles token refresh."
        assert result[1]["pattern_id"] == "id-2"
        assert result[1]["pattern_name"] == "Redis Cache Pattern"

    def test_empty_table(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []

        result = fetch_existing_patterns(mock_conn, "new-repo")

        assert result == []

    def test_null_description(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            ("id-1", "Some Pattern", None),
        ]

        result = fetch_existing_patterns(mock_conn, "my-repo")

        assert result[0]["description"] == ""


class TestLoadFreshCards:
    def test_loads_json(self, tmp_path):
        cards = [
            {"pattern_name": "Test", "repo_name": "my-repo"},
            {"pattern_name": "Other", "repo_name": "my-repo"},
        ]
        path = tmp_path / "cards.json"
        path.write_text(json.dumps(cards))

        result = load_fresh_cards(str(path))

        assert len(result) == 2
        assert result[0]["pattern_name"] == "Test"

    def test_empty_list(self, tmp_path):
        path = tmp_path / "empty.json"
        path.write_text("[]")

        result = load_fresh_cards(str(path))

        assert result == []
