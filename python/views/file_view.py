import discord
from .file_dropdown import FileDropDown
from .file_button import FileButton
from ..search.discord_searcher import DiscordSearcher
from ..search.search_models import SearchResults


class FileView(discord.ui.View):
    def __init__(self, files: SearchResults, search_client: DiscordSearcher):
        super().__init__()
        # you can store the maps per "page" in this view itself
        # this way going backwards is deterministic
        # but seriously, the more correct way of handling this is to crawl a server, and then store files
        # probably worth just crawling a server and building indices for it
        # let's apply some of the knowledge we've gained here...
        # worth creating a pricing model for this too actually...
        # 

        # then let's build the generalized search...
        # this problem is slightly easier because we have generic documents that we need to search
        # don't need to solve the garbage problem - but I don't think this will really be a problem given enough data

        if len(files.files) <= 5:
            for file in files.files:
                self.add_item(FileButton(file))
        else:
            self.add_item(FileDropDown(files))
        self.add_item(PaginationButton(files, search_client))
