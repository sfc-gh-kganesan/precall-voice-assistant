"""
Tests for the context factory.

The factory inspects SNOWFLAKE_HOST at call time to choose between
CortexContext (SPCS runner) and LocalBackend (local / CI).  Heavy
dependencies are patched at their source modules so tests run
without snowflake-connector-python installed.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch


class TestContextFactory:

    def test_returns_cortex_context_when_snowflake_host_set(self, monkeypatch):
        """When SNOWFLAKE_HOST is set, create_context() returns a CortexContext."""
        monkeypatch.setenv("SNOWFLAKE_HOST", "myaccount.snowflakecomputing.com")

        mock_instance = MagicMock()
        mock_cls = MagicMock(return_value=mock_instance)

        with patch("p67_sdk.cortex_context.CortexContext", mock_cls):
            from p67_sdk.context_factory import create_context
            ctx = create_context()

        mock_cls.assert_called_once()
        assert ctx is mock_instance

    def test_returns_local_backend_when_no_snowflake_host(self, monkeypatch):
        """When SNOWFLAKE_HOST is absent, create_context() returns a LocalBackend."""
        monkeypatch.delenv("SNOWFLAKE_HOST", raising=False)

        mock_sdk_instance = MagicMock()
        mock_sdk_cls = MagicMock(return_value=mock_sdk_instance)
        mock_backend_instance = MagicMock()
        mock_backend_cls = MagicMock(return_value=mock_backend_instance)

        with (
            patch("p67_sdk.sdk.WorkflowSDK", mock_sdk_cls),
            patch("p67_sdk.local_backend.LocalBackend", mock_backend_cls),
        ):
            from p67_sdk.context_factory import create_context
            ctx = create_context()

        mock_backend_cls.assert_called_once()
        assert ctx is mock_backend_instance

    def test_passes_config_to_workflow_sdk(self, monkeypatch):
        """The config dict is forwarded unchanged to the WorkflowSDK constructor."""
        monkeypatch.delenv("SNOWFLAKE_HOST", raising=False)

        config = {"snowflakeConfig": {"default": {"account": "myaccount"}}}
        mock_sdk_cls = MagicMock()
        mock_backend_cls = MagicMock()

        with (
            patch("p67_sdk.sdk.WorkflowSDK", mock_sdk_cls),
            patch("p67_sdk.local_backend.LocalBackend", mock_backend_cls),
        ):
            from p67_sdk.context_factory import create_context
            create_context(config=config)

        mock_sdk_cls.assert_called_once_with(config)

    def test_passes_kwargs_to_cortex_context(self, monkeypatch):
        """Extra keyword arguments are forwarded to the CortexContext constructor."""
        monkeypatch.setenv("SNOWFLAKE_HOST", "myaccount.snowflakecomputing.com")

        mock_cls = MagicMock()

        with patch("p67_sdk.cortex_context.CortexContext", mock_cls):
            from p67_sdk.context_factory import create_context
            create_context(token_path="/custom/token")

        mock_cls.assert_called_once_with(token_path="/custom/token")

    def test_empty_config_still_creates_sdk(self, monkeypatch):
        """create_context() with no config arg does not raise when creating LocalBackend."""
        monkeypatch.delenv("SNOWFLAKE_HOST", raising=False)

        mock_sdk_cls = MagicMock()
        mock_backend_cls = MagicMock()

        with (
            patch("p67_sdk.sdk.WorkflowSDK", mock_sdk_cls),
            patch("p67_sdk.local_backend.LocalBackend", mock_backend_cls),
        ):
            from p67_sdk.context_factory import create_context
            create_context()

        mock_sdk_cls.assert_called_once_with({})

    def test_cortex_context_not_created_when_no_host(self, monkeypatch):
        """CortexContext constructor is never called in the local-backend path."""
        monkeypatch.delenv("SNOWFLAKE_HOST", raising=False)

        mock_cortex_cls = MagicMock()
        mock_sdk_cls = MagicMock()
        mock_backend_cls = MagicMock()

        with (
            patch("p67_sdk.cortex_context.CortexContext", mock_cortex_cls),
            patch("p67_sdk.sdk.WorkflowSDK", mock_sdk_cls),
            patch("p67_sdk.local_backend.LocalBackend", mock_backend_cls),
        ):
            from p67_sdk.context_factory import create_context
            create_context()

        mock_cortex_cls.assert_not_called()
