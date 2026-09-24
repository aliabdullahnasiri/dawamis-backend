import asyncio
from typing import Any

from app.types import AsyncService
from app.workers.base import BaseWorker


class EmailWorker(BaseWorker):
    name = "email.send"

    @staticmethod
    def send(
        service: AsyncService,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        asyncio.run(
            service(
                *args,
                **kwargs,
            )
        )
