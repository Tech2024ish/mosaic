import uuid
from collections.abc import Callable
from typing import Protocol

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy.orm.session import sessionmaker

from app.infrastructure.storage.local import LocalFileStorage


class ImportJobExecutor(Protocol):
    def submit(self, job_id: uuid.UUID) -> None: ...


class BackgroundTasksImportExecutor:
    """Current in-process adapter behind the future durable job boundary."""

    def __init__(
        self,
        background_tasks: BackgroundTasks,
        processor: Callable[[uuid.UUID, LocalFileStorage, sessionmaker[Session]], None],
        storage: LocalFileStorage,
        session_factory: sessionmaker[Session],
    ) -> None:
        self.background_tasks = background_tasks
        self.processor = processor
        self.storage = storage
        self.session_factory = session_factory

    def submit(self, job_id: uuid.UUID) -> None:
        self.background_tasks.add_task(self.processor, job_id, self.storage, self.session_factory)
