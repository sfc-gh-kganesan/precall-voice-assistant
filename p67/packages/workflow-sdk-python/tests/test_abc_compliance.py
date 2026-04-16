"""Tests that all AutomationContext implementations satisfy the ABC contract."""


class TestABCCompliance:
    def test_cortex_context_is_automation_context(self):
        """CortexContext is a subclass of AutomationContext."""
        from p67_sdk.automation_context import AutomationContext
        from p67_sdk.cortex_context import CortexContext
        assert issubclass(CortexContext, AutomationContext)

    def test_mock_cortex_context_is_automation_context(self):
        """MockCortexContext is a subclass of AutomationContext."""
        from p67_sdk.automation_context import AutomationContext
        from p67_sdk.mock_cortex_context import MockCortexContext
        assert issubclass(MockCortexContext, AutomationContext)

    def test_local_backend_is_automation_context(self):
        """LocalBackend is a subclass of AutomationContext."""
        from p67_sdk.automation_context import AutomationContext
        from p67_sdk.local_backend import LocalBackend
        assert issubclass(LocalBackend, AutomationContext)

    def test_automation_context_cannot_be_instantiated(self):
        """AutomationContext ABC cannot be instantiated directly."""
        import pytest
        from p67_sdk.automation_context import AutomationContext
        with pytest.raises(TypeError):
            AutomationContext()
