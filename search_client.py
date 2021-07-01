"""A small abstract class to ensure implementations for basic functions exist."""
from abc import ABC, abstractmethod


class AsyncSearchClient(ABC):
    """Basic Requirements for any Search Client in this project."""

    @abstractmethod
    async def create_doc(self, *args, **kwargs):
        """Create a doc in the Search Index."""
        pass

    @abstractmethod
    async def remove_doc(self, *args, **kwargs):
        """Remove a doc in the Search Index."""
        pass

    @abstractmethod
    async def search(self, *args, **kwargs):
        """Search for a doc in the Search Index."""
        pass
