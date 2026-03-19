# P67 Quickstart

## New TypeScript Workflow

```bash
p67 init myworkflow --language typescript
cd myworkflow
# edit src/index.ts
p67 build
p67 workflow deploy
p67 workflow run --name myworkflow
```

## New Python Workflow

```bash
p67 init myworkflow --language python
cd myworkflow
# edit src/main.py
p67 build
p67 workflow deploy
p67 workflow run --name myworkflow
```

## With Parameters

```bash
p67 workflow run --name myworkflow -p KEY1=value1 -p KEY2=value2
```

## With Secrets

```bash
echo "your-api-key-here" | p67 secret save MY_API_KEY
p67 build && p67 workflow deploy --overwrite
p67 workflow run --name myworkflow
```

## Check Results

```bash
p67 workflow runs --name myworkflow --limit 5
p67 logs list --run <runId>
```
