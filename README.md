# Codespace Workspace - Claude Skill for GitHub Codespaces

A Python-based Codespace (Virtual Desktop Infrastructure) agent that runs inside GitHub Codespaces, exposing file system and command execution capabilities via a REST API. This project includes a Claude Skill that enables coding agents to interact with the Codespace programmatically.

## Overview

This repository provides:

1. **Codespace Agent**: A FastAPI-based service that exposes endpoints for file operations and command execution
2. **Claude Skill**: A skill definition that enables Claude and other coding agents to work with the Codespace
3. **Dev Container Configuration**: Automatic setup and deployment in GitHub Codespaces

## Architecture

```text
codespace-skill/
  ├── codespace-agent/
  │   ├── app.py              # FastAPI application
  │   └── requirements.txt     # Python dependencies
  ├── codespace-workspace/
  │   └── SKILL.md             # Claude skill definition
  ├── .devcontainer/
  │   └── devcontainer.json    # Codespace configuration
  ├── INIT.md                  # Bootstrap instructions
  └── README.md                # This file
```

## Features

### Codespace Agent API Endpoints

- **POST /exec**: Execute shell commands
  - Parameters: `command`, `cwd` (optional), `timeout_seconds` (default: 120)
  - Returns: `exit_code`, `stdout`, `stderr`

- **POST /fs/read**: Read file contents
  - Parameters: `path`
  - Returns: `path`, `content`

- **POST /fs/write**: Write file contents
  - Parameters: `path`, `content`, `create_parents` (default: true)
  - Returns: `path`, `bytes_written`

### Interactive API Documentation

FastAPI automatically generates interactive API documentation available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Getting Started

### Quick Start with GitHub Codespaces

1. Click "Code" → "Create codespace on main"
2. Wait for the container to build and start (the Codespace agent starts automatically)
3. Verify the agent is running:
   ```bash
   curl http://localhost:8000/docs
   ```

### Manual Setup

If you're not using the devcontainer auto-start:

1. Install dependencies:
   ```bash
   pip install -r codespace-agent/requirements.txt
   ```

2. Start the Codespace agent:
   ```bash
   uvicorn codespace-agent.app:app --host 0.0.0.0 --port 8000
   ```

3. Test the endpoints:
   ```bash
   # Test command execution
   curl -X POST http://localhost:8000/exec \
     -H "Content-Type: application/json" \
     -d '{"command": "ls -la", "cwd": "."}'

   # Test file write
   curl -X POST http://localhost:8000/fs/write \
     -H "Content-Type: application/json" \
     -d '{"path": "test.txt", "content": "Hello World", "create_parents": true}'

   # Test file read
   curl -X POST http://localhost:8000/fs/read \
     -H "Content-Type: application/json" \
     -d '{"path": "test.txt"}'
   ```

## Using the Claude Skill

The `codespace-workspace` skill enables Claude and other coding agents to interact with this Codespace. The skill provides guidelines for:

- Discovering the project structure
- Planning and making changes safely
- Running tests and checks
- Following best practices for file operations

See [codespace-workspace/SKILL.md](codespace-workspace/SKILL.md) for the complete skill definition.

### Example Workflow

1. Discover the project:
   ```bash
   curl -X POST http://localhost:8000/exec \
     -H "Content-Type: application/json" \
     -d '{"command": "ls -la"}'
   ```

2. Read a file:
   ```bash
   curl -X POST http://localhost:8000/fs/read \
     -H "Content-Type: application/json" \
     -d '{"path": "codespace-agent/app.py"}'
   ```

3. Modify and write back:
   ```bash
   curl -X POST http://localhost:8000/fs/write \
     -H "Content-Type: application/json" \
     -d '{"path": "codespace-agent/app.py", "content": "..."}'
   ```

4. Run tests:
   ```bash
   curl -X POST http://localhost:8000/exec \
     -H "Content-Type: application/json" \
     -d '{"command": "pytest", "cwd": "."}'
   ```

## Integration with OpenSkills

To use this skill with multiple coding agents (Cursor, Windsurf, Aider, etc.):

1. Install OpenSkills:
   ```bash
   npm install -g openskills
   ```

2. Install the skill:
   ```bash
   openskills install <your-username>/codespace-skill --universal
   ```

3. Sync to generate AGENTS.md:
   ```bash
   openskills sync
   ```

## Development

### Adding New Endpoints

1. Edit `codespace-agent/app.py`
2. Define request/response models using Pydantic
3. Add the endpoint function with proper error handling
4. Update this README and the skill documentation

### Security Considerations

- The Codespace agent runs with the same permissions as the Codespace user
- Commands are executed via shell with subprocess
- File operations are restricted to the Codespace filesystem
- Always validate and sanitize inputs in production environments
- Consider adding authentication for production deployments

## Resources

- [Anthropic Skills Repository](https://github.com/anthropics/skills)
- [OpenSkills](https://github.com/numman-ali/openskills)
- [Open-Skills MCP Server](https://github.com/BandarLabs/open-skills)
- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [GitHub Codespaces Documentation](https://docs.github.com/codespaces)

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
