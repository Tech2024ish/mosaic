import hashlib
import uuid
from pathlib import Path
from typing import BinaryIO

from fastapi import UploadFile


class FileTooLargeError(ValueError):
    pass


class LocalFileStorage:
    def __init__(self, root: str, max_size_bytes: int) -> None:
        self.root = Path(root).resolve()
        self.max_size_bytes = max_size_bytes
        self.root.mkdir(parents=True, exist_ok=True)

    async def save_upload(self, upload: UploadFile) -> tuple[str, int, str]:
        key = f"{uuid.uuid4()}.upload"
        destination = self.root / key
        digest = hashlib.sha256()
        size = 0
        try:
            with destination.open("wb") as output:
                while chunk := await upload.read(1024 * 1024):
                    size += len(chunk)
                    if size > self.max_size_bytes:
                        raise FileTooLargeError(f"Upload exceeds {self.max_size_bytes} bytes")
                    digest.update(chunk)
                    output.write(chunk)
        except Exception:
            destination.unlink(missing_ok=True)
            raise
        return key, size, digest.hexdigest()

    def open(self, key: str) -> BinaryIO:
        path = (self.root / key).resolve()
        if path.parent != self.root or not path.is_file():
            raise FileNotFoundError("Stored upload not found")
        return path.open("rb")

    def delete(self, key: str) -> None:
        path = (self.root / key).resolve()
        if path.parent == self.root:
            path.unlink(missing_ok=True)
