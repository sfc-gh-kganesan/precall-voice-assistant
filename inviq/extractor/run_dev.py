from py_util.dev_server import run_dev_server

if __name__ == "__main__":
    run_dev_server(
        server_command="uv run python -m app.main",
        watch_path="./app",
        match_pattern=r".*\.py$",
    )
