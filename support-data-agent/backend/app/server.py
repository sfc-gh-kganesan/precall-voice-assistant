#!/usr/bin/env python3
"""Production server entrypoint."""

import uvicorn


def main():
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
