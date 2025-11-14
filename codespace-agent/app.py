from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
import subprocess
from typing import List
import re
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s"
)
logger = logging.getLogger("codespace_agent")

app = FastAPI(
    title="Codespace Agent API",
    description="A REST API for file operations and command execution in GitHub Codespaces",
    version="1.0.0"
)

# Add CORS middleware to allow web-based clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ExecRequest(BaseModel):
    command: str
    cwd: str | None = None
    timeout_seconds: int = 120


class ExecResponse(BaseModel):
    exit_code: int
    stdout: str
    stderr: str


class ReadRequest(BaseModel):
    path: str


class ReadResponse(BaseModel):
    path: str
    content: str


class WriteRequest(BaseModel):
    path: str
    content: str
    create_parents: bool = True


class WriteResponse(BaseModel):
    path: str
    bytes_written: int


@app.post("/exec", response_model=ExecResponse)
def exec_command(req: ExecRequest):
    cwd = req.cwd or str(Path(".").resolve())
    logger.info("exec request command=%s cwd=%s timeout=%s", req.command, cwd, req.timeout_seconds)
    try:
        result = subprocess.run(
            req.command,
            cwd=cwd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=req.timeout_seconds,
        )
    except subprocess.TimeoutExpired as e:
        logger.error("exec timeout command=%s cwd=%s timeout=%s", req.command, cwd, req.timeout_seconds)
        raise HTTPException(status_code=408, detail=f"Command timed out: {e}")

    logger.info(
        "exec response exit_code=%s stdout_len=%s stderr_len=%s",
        result.returncode,
        len(result.stdout),
        len(result.stderr),
    )
    return ExecResponse(
        exit_code=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
    )


@app.post("/fs/read", response_model=ReadResponse)
def read_file(req: ReadRequest):
    path = Path(req.path)
    logger.info("fs.read request path=%s", path)
    if not path.is_file():
        logger.warning("fs.read missing path=%s", path)
        raise HTTPException(status_code=404, detail="File not found")
    content = path.read_text(encoding="utf-8")
    logger.info("fs.read path=%s bytes=%s", path, len(content.encode("utf-8")))
    return ReadResponse(path=str(path), content=content)


@app.post("/fs/write", response_model=WriteResponse)
def write_file(req: WriteRequest):
    path = Path(req.path)
    if req.create_parents:
        path.parent.mkdir(parents=True, exist_ok=True)
    data = req.content.encode("utf-8")
    logger.info("fs.write request path=%s create_parents=%s bytes=%s", path, req.create_parents, len(data))
    path.write_bytes(data)
    logger.info("fs.write path=%s bytes=%s create_parents=%s", path, len(data), req.create_parents)
    return WriteResponse(path=str(path), bytes_written=len(data))


class DeleteRequest(BaseModel):
    path: str
    recursive: bool = False


class DeleteResponse(BaseModel):
    path: str
    deleted: bool


class ListDirRequest(BaseModel):
    path: str = "."
    include_hidden: bool = False


class FileInfo(BaseModel):
    name: str
    path: str
    is_file: bool
    is_dir: bool
    size: int | None = None


class ListDirResponse(BaseModel):
    path: str
    files: List[FileInfo]


class SearchRequest(BaseModel):
    pattern: str
    path: str = "."
    file_pattern: str | None = None
    max_results: int = 100


class SearchMatch(BaseModel):
    file_path: str
    line_number: int
    line_content: str


class SearchResponse(BaseModel):
    pattern: str
    matches: List[SearchMatch]
    total_matches: int


class HealthResponse(BaseModel):
    status: str
    version: str


@app.get("/health", response_model=HealthResponse)
def health_check():
    """Health check endpoint for monitoring"""
    logger.info("health check request")
    return HealthResponse(status="healthy", version="1.0.0")


@app.post("/fs/delete", response_model=DeleteResponse)
def delete_file(req: DeleteRequest):
    """Delete a file or directory"""
    path = Path(req.path)
    logger.info("fs.delete request path=%s recursive=%s", path, req.recursive)

    if not path.exists():
        logger.warning("fs.delete missing path=%s", path)
        raise HTTPException(status_code=404, detail="Path not found")

    try:
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            if req.recursive:
                import shutil
                shutil.rmtree(path)
            else:
                path.rmdir()
        logger.info("fs.delete path=%s recursive=%s", path, req.recursive)
        return DeleteResponse(path=str(path), deleted=True)
    except OSError as e:
        logger.error("fs.delete failed path=%s recursive=%s error=%s", path, req.recursive, e)
        raise HTTPException(status_code=500, detail=f"Failed to delete: {e}")


@app.post("/fs/list", response_model=ListDirResponse)
def list_directory(req: ListDirRequest):
    """List contents of a directory"""
    path = Path(req.path)
    logger.info("fs.list request path=%s include_hidden=%s", path, req.include_hidden)

    if not path.exists():
        logger.warning("fs.list missing path=%s", path)
        raise HTTPException(status_code=404, detail="Directory not found")

    if not path.is_dir():
        logger.warning("fs.list not_directory path=%s", path)
        raise HTTPException(status_code=400, detail="Path is not a directory")

    files = []
    for item in path.iterdir():
        if not req.include_hidden and item.name.startswith('.'):
            continue

        file_info = FileInfo(
            name=item.name,
            path=str(item),
            is_file=item.is_file(),
            is_dir=item.is_dir(),
            size=item.stat().st_size if item.is_file() else None
        )
        files.append(file_info)

    # Sort: directories first, then files, both alphabetically
    files.sort(key=lambda x: (not x.is_dir, x.name.lower()))

    logger.info("fs.list path=%s count=%s include_hidden=%s", path, len(files), req.include_hidden)
    return ListDirResponse(path=str(path), files=files)


@app.post("/fs/search", response_model=SearchResponse)
def search_files(req: SearchRequest):
    """Search for text pattern in files"""
    search_path = Path(req.path)
    logger.info(
        "fs.search request pattern=%s path=%s file_pattern=%s max_results=%s",
        req.pattern,
        search_path,
        req.file_pattern,
        req.max_results,
    )

    if not search_path.exists():
        logger.warning("fs.search path_not_found path=%s", search_path)
        raise HTTPException(status_code=404, detail="Search path not found")

    matches = []
    pattern = re.compile(req.pattern)

    # Determine which files to search
    if search_path.is_file():
        files_to_search = [search_path]
    else:
        if req.file_pattern:
            file_glob = re.compile(req.file_pattern)
            files_to_search = [
                f for f in search_path.rglob("*")
                if f.is_file() and file_glob.search(str(f))
            ]
        else:
            files_to_search = [f for f in search_path.rglob("*") if f.is_file()]

    for file_path in files_to_search:
        if len(matches) >= req.max_results:
            break

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    if pattern.search(line):
                        matches.append(SearchMatch(
                            file_path=str(file_path),
                            line_number=line_num,
                            line_content=line.rstrip()
                        ))
                        if len(matches) >= req.max_results:
                            break
        except Exception:
            # Skip files that can't be read
            continue

    logger.info(
        "fs.search pattern=%s path=%s file_pattern=%s matches=%s",
        req.pattern,
        search_path,
        req.file_pattern,
        len(matches),
    )
    return SearchResponse(
        pattern=req.pattern,
        matches=matches,
        total_matches=len(matches)
    )
