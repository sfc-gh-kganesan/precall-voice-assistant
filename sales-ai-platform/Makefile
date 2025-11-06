# Makefile compatibility shim for sales-ai-platform
# This project uses justfile - this Makefile automatically installs just and delegates to it.

# List of all targets from justfile (to avoid conflicts)
TARGETS := help install dev api studio check-env deploy status logs url check fmt clean

.PHONY: _ensure-just $(TARGETS)

# Default target
.DEFAULT_GOAL := help

# Check if just is installed, install it if not
_ensure-just:
	@if ! command -v just &> /dev/null; then \
		echo "📦 just is not installed. Installing via Homebrew..."; \
		brew install just; \
		echo "✅ just installed successfully"; \
		echo ""; \
		echo "💡 Tip: You can now use 'just' directly instead of 'make'"; \
		echo "   - Use arguments: just dev 3000"; \
		echo "   - Use aliases: just fmt, just logs"; \
		echo "   - Private recipes: just _connection-flag"; \
		echo ""; \
	fi

# Create a target for each just recipe
$(TARGETS): _ensure-just
	@just $@
