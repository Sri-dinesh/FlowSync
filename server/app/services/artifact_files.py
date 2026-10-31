"""Atomic replacement of a complete local artifact."""
import os
from pathlib import Path
import tempfile


def write_bytes_atomic(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    descriptor,name = tempfile.mkstemp(prefix=f".{path.name}.",suffix=".tmp",dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor,"wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary,path)
    finally:
        temporary.unlink(missing_ok=True)
