# p67 UI

# 1. Install `uv`

```bash
brew install uv
```

if you don't have bash

Run

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

# 2. Set up environment

```bash
uv venv
uv pip install --requirements requirements.txt
```

# 3. Run the app

```bash
uv run app.py
```

This will yield something like the following to the command line:

```
 * Serving Flask app 'app'
 * Debug mode: on
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on http://127.0.0.1:5001
Press CTRL+C to quit
```

Go to [](http://127.0.0.1:5001) to see the tool.

# 4. Edit a workflow

By default, there's added `example.workflow.json`. Select it on the left panel as `example`.
