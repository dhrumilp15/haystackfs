import discord
from .file_dropdown import FileDropDown
from .file_button import FileButton
from ..search.search_models import SearchResults


class FileView(discord.ui.View):
    def __init__(self, files: SearchResults):
        super().__init__()
        if len(files.files) <= 5:
            for file in files.files:
                self.add_item(FileButton(file))
        else:
            self.add_item(FileDropDown(files))
