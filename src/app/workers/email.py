from typing import Any

from app.types import AsyncService
from app.workers.base import BaseWorker


class EmailWorker(BaseWorker):
    name = "email.send"

    @staticmethod
    async def send(
        service: AsyncService,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        await service(
            *args,
            **kwargs,
        )
