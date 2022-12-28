"""A small abstract class to ensure implementations for basic functions exist."""
from abc import ABC, abstractmethod


class AsyncDataClient(ABC):
    """Basic Requirements for any Search Client in this project."""

    @abstractmethod
    async def log_command(self, *args, **kwargs):
        """Log a command."""
        pass
