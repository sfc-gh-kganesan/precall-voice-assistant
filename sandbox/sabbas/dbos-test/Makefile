.PHONY: help install run test clean

help:
	@echo "DBOS FastAPI Queue Example"
	@echo ""
	@echo "Available commands:"
	@echo "  make install    - Install dependencies"
	@echo "  make run        - Run the FastAPI server"
	@echo "  make test       - Run the test script (server must be running)"
	@echo "  make clean      - Clean up generated files"
	@echo ""

install:
	uv sync

run:
	@echo "🚀 Starting FastAPI server with DBOS..."
	@echo "📍 Server will be available at http://localhost:8000"
	@echo "📖 API docs at http://localhost:8000/docs"
	@echo ""
	uv run python main.py

dev:
	@echo "🔧 Starting in development mode with auto-reload..."
	uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000

test:
	@echo "🧪 Running API tests..."
	@echo ""
	uv run python test_api.py

clean:
	@echo "🧹 Cleaning up..."
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -rf *.egg-info
	rm -f *.db
	rm -f *.db-journal
	@echo "✅ Cleanup complete!"

