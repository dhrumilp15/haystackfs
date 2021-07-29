"""A Search Client for Algolia."""
from algoliasearch.search_client import SearchClient
from algoliasearch.exceptions import RequestException
from config import CONFIG
from .async_search_client import AsyncSearchClient
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='algolia_client.log', encoding='utf-8', mode='w')
formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


class AlgoliaClient(AsyncSearchClient):
    """A Search Client for Algolia."""

    def __init__(self, app_id=None, search_key=None, admin_key=None):
        """Init Search and Admin clients."""
        self.search_client = None
        self.admin_client = None
        if app_id and search_key and admin_key:
            self.search_client = SearchClient.create(app_id, search_key)
            self.admin_client = SearchClient.create(app_id, admin_key)

    def initialize(self, *args, **kwargs):
        """Initialize client."""
        pass

    def show_indices(self):
        """Print all indices."""
        if self.admin_client:
            print(self.admin_client.list_indices())

    def create_filter(self, **kwargs) -> str:
        """Construct a search filter."""
        search_filter = []
        if kwargs.get("mimetype"):
            search_filter.append(f"mimetype = {kwargs['mimetype']}")
        if kwargs.get("author"):
            search_filter.append(f"author = {kwargs['author']}")
        if kwargs.get("channel"):
            search_filter.append(f"channel = {kwargs['channel']}")
        if kwargs.get("content"):
            content = kwargs["content"]
            search_filter.append(f"content = '{content}'")
        if kwargs.get("before") and kwargs.get("after"):
            search_filter.append(
                f"ObjectID: {kwargs['before']} TO {kwargs['after']}")
        elif kwargs.get("after"):
            search_filter.append(f"ObjectID > {kwargs['after']}")
        elif kwargs.get("before"):
            search_filter.append(f"ObjectID < {kwargs['before']}")
        return ' AND '.join(search_filter)

    async def search(self, filename: str, serv_id: int, *args, **kwargs) -> List[Dict]:
        """
        Search for files.

        Args:
            filename: The filename to search.
            serv_id: The id of the server/channel to search in.

        Returns:
            Search results.
        """
        if not self.search_client:
            logger.info("self.search_client not initialized, returning []")
            return []
        async with self.search_client as client:
            index = client.init_index(CONFIG.DB_NAME + '_' + str(serv_id))
            filters = self.create_filter(**kwargs)
            try:
                res = await index.search_async(filename, {
                    "advancedSyntax": True,
                    "filters": filters
                })
                try:
                    return (await res)['hits']
                except BaseException as e:
                    return res["hits"]
            except RequestException as err:
                return []

    async def create_doc(self, meta_dict: dict, serv_id: int, author: str) -> bool:
        """
        Create doc in Aloglia Index.

        Args:
            meta_dict: A dict of metadata about a file
            serv_id: The id of the server/guild.
            author: A str repr of the author.
        Returns:
            Whether the operation was executed.
        """
        if not self.admin_client:
            return False
        async with self.admin_client as client:
            index = client.init_index(CONFIG.DB_NAME + '_' + str(serv_id))
            res = await index.save_object_async(meta_dict, {
                "autoGenerateObjectIDIfNotExist": False,
                "X-Algolia-UserToken": author
            })
            return bool(res)

    async def remove_doc(self, ids: List[str], serv_id: int, author: str, **kwargs) -> bool:
        """
        Remove docs.

        Args:
            filename: The filename of docs to remove.
            serv_id: The server id in which to remove the docs.
            author: The author of the command to remove docs.

        Returns:
            Whether the remove operation succeeded.
        """
        if not self.admin_client:
            return False
        async with self.admin_client as client:
            index = client.init_index(CONFIG.DB_NAME + '_' + str(serv_id))
            res = await index.delete_objects_async(ids, {
                "X-Algolia-UserToken": author
            })
            return res

    async def get_all_docs(self, serv_id: int) -> List[Dict]:
        """Retrieve all docs in an index."""
        if not self.search_client:
            return []
        async with self.search_client as client:
            index = client.init_index(CONFIG.DB_NAME + '_' + str(serv_id))
            res = await index.search_async('')
            return res['hits']

    async def clear(self, serv_id: int):
        """Clear an index."""
        if not self.admin_client:
            return False
        async with self.admin_client as client:
            index = client.init_index(CONFIG.DB_NAME + '_' + str(serv_id))
            res = await index.clear_objects_async()
            return res


if __name__ == "__main__":
    ag_client = AlgoliaClient()
