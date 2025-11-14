---
name: codespace-workspace
description: >
  Work with this git-based project running in a GitHub Codespace/devcontainer
  by calling a Python service that can read/write files and execute commands.
---

# Codespace Workspace Skill

When the user wants you to modify or inspect this repository, use this skill
to orchestrate work through the Python Codespace agent running on port 8000 inside
the devcontainer/Codespace.

## Connection Setup

Each Codespace session generates a new public URL, so the agent cannot assume
a fixed hostname.

1. The devcontainer automatically launches `uvicorn codespace-agent.app:app --host 0.0.0.0 --port 8000`.
2. The Codespace operator must publish port `8000` so it becomes publicly reachable.
3. Ask the operator for the resulting base URL (e.g., `https://8000-<codespace>.app.github.dev`) and store it as `BASE_URL`.
4. Use that URL for every API call (`$BASE_URL/exec`, `$BASE_URL/fs/read`, etc.).
5. If the operator has not provided the base URL, pause and request it before proceeding.

## Capabilities

The Codespace agent exposes an HTTP API with the following endpoints:

### Core Endpoints
- `GET /health` - Health check for monitoring
- `POST /exec` - Execute shell commands
- `POST /fs/read` - Read file contents
- `POST /fs/write` - Write file contents
- `POST /fs/delete` - Delete files or directories
- `POST /fs/list` - List directory contents
- `POST /fs/search` - Search for text patterns in files

You can call these endpoints from the shell (Bash tool) using `curl`.

### Interactive Documentation
The API includes auto-generated interactive documentation:
- Swagger UI: `$BASE_URL/docs`
- ReDoc: `$BASE_URL/redoc`

### Run a command

```bash
curl -s -X POST "$BASE_URL/exec" \
  -H "Content-Type: application/json" \
  -d '{"command": "pytest", "cwd": "."}'
```

### Read a file

```bash
curl -s -X POST "$BASE_URL/fs/read" \
  -H "Content-Type: application/json" \
  -d '{"path": "src/app.py"}'
```

### Write a file

```bash
cat << 'EOF' > /tmp/codespace-write.json
{
  "path": "src/app.py",
  "content": "<NEW_FILE_CONTENT>",
  "create_parents": true
}
EOF

curl -s -X POST "$BASE_URL/fs/write" \
  -H "Content-Type: application/json" \
  -d @/tmp/codespace-write.json
```

Replace `<NEW_FILE_CONTENT>` with the full, updated file contents.

### List directory contents

```bash
curl -s -X POST "$BASE_URL/fs/list" \
  -H "Content-Type: application/json" \
  -d '{"path": ".", "include_hidden": false}'
```

### Delete a file

```bash
curl -s -X POST "$BASE_URL/fs/delete" \
  -H "Content-Type: application/json" \
  -d '{"path": "test.txt", "recursive": false}'
```

For directories, set `"recursive": true` to delete recursively.

### Search for text in files

```bash
curl -s -X POST "$BASE_URL/fs/search" \
  -H "Content-Type: application/json" \
  -d '{"pattern": "TODO", "path": ".", "max_results": 50}'
```

You can optionally specify a `file_pattern` to filter which files to search (e.g., `"file_pattern": ".*\\.py$"` to search only Python files).

### Check health status

```bash
curl -s "$BASE_URL/health"
```

## Workflow Guidelines

1. **Discover the project**
   - Use `/fs/list` to browse directory contents efficiently.
   - Use `/fs/search` to find specific patterns or TODOs in the codebase.
   - Use `/exec` with project-specific tools if needed.
   - Look for config like `pyproject.toml`, `requirements.txt`, `package.json`,
     `devcontainer.json` to infer language and tooling.

2. **Plan changes**
   - Identify which files will be changed.
   - Summarize the intended edits before making them.

3. **Edit files safely**
   - Always use `/fs/read` first to get existing content.
   - Synthesize complete new file content and write via `/fs/write`.
   - Avoid partial edits with sed/awk when possible; prefer full-file rewrites.

4. **Run checks**
   - Use `/exec` to run tests or formatters:
     - e.g. `pytest`, `python -m pytest`, `ruff`, `black`, or project-specific commands.
   - Report back exit codes and relevant output.

5. **Safety**
   - Do not run destructive commands like `rm -rf .` at the repo root.
   - Prefer idempotent, local actions.
   - If unsure about a command that could be destructive, explain the plan and ask the user to confirm first.

## Example Tasks

- "Add a /refund endpoint to the API and run tests."
- "Refactor a module into smaller functions, then run the formatter and tests."
- "Create a basic CI config file and run the project's test command."

You can later add more examples, references, or helper scripts into `codespace-workspace/references/` or `scripts/`, following patterns from `anthropics/skills`.
