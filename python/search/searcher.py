"""Main class for search."""
from .async_search_client import AsyncSearchClient
from typing import List, Dict


class Searcher(AsyncSearchClient):
    """A 'main' class for search."""

    def __init__(self, *args):
        """
        Create a Searcher.

        Args:
            args: Existing AsyncSearchClients. Searcher will search the query on each one.
        """
        self.search_clients = args

    def initialize(self, *args, **kwargs):
        """Initialize each search client."""
        for sc in self.search_clients:
            sc.initialize(*args, **kwargs)

    async def search(self, filename: str, serv, *args, **kwargs) -> List[Dict]:
        """
        Search using all async search clients.

        Args:
            filename: The filename to search for
            serv_id: The channel/guild to search in
            kwargs: Any search options.

        Returns:
            A list of files that match the search criteria with no duplicate file ids.
        """
        files = []
        for search_client in self.search_clients:
            res = await search_client.search(filename, serv, *args, **kwargs)
            files.extend(res)
        # files = [val async for search_client in self.search_clients for val in ]
        ids = set()
        no_duplicate_files = []
        for file in files:
            if file['objectID'] not in ids:
                no_duplicate_files.append(file)
                ids.add(file['objectID'])
        return no_duplicate_files

    async def create_doc(self, *args, **kwargs):
        """Create docs in each search client."""
        for sc in self.search_clients:
            await sc.create_doc(*args, **kwargs)

    async def remove_doc(self, *args, **kwargs):
        """Delete docs in each search client."""
        for sc in self.search_clients:
            await sc.remove_doc(*args, **kwargs)
