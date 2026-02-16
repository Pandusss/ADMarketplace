from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable, Generic, TypeVar

T = TypeVar("T")
logger = logging.getLogger(__name__)

Handler = Callable[[T], Awaitable[None]]


class Signal(Generic[T]):
    """
    A simple async signal implementation for internal events.
    """
    def __init__(self, name: str):
        self.name = name
        self._handlers: list[Handler[T]] = []

    def connect(self, handler: Handler[T]):
        """Register a handler for this signal."""
        if handler not in self._handlers:
            self._handlers.append(handler)
            logger.debug(f"Signal '{self.name}': handler {handler.__name__} connected.")

    async def emit(self, data: T):
        """
        Emit the signal, calling all registered handlers concurrently.
        """
        if not self._handlers:
            return

        tasks = []
        for handler in self._handlers:
            tasks.append(self._run_handler(handler, data))

        await asyncio.gather(*tasks, return_exceptions=True)

    async def _run_handler(self, handler: Handler[T], data: T):
        try:
            await handler(data)
        except Exception as e:
            logger.error(f"Error in signal '{self.name}' handler {handler.__name__}: {e}", exc_info=True)
