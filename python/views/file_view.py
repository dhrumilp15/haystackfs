import discord
from .file_dropdown import FileDropDown
from .file_button import FileButton
from .page_back_button import PageBackButton
from .page_next_button import PageNextButton
from ..bot_commands import fsearch
from ..models.query import Query
from ..search.discord_searcher import DiscordSearcher
from ..search.search_models import SearchResults, SearchResult
import re


class FileView(discord.ui.View):
    def __init__(self, results: SearchResults, search_client: DiscordSearcher, query: Query):
        super().__init__()
        self.pages = {1: results}
        self.current_page = 1
        self.query = query
        self.search_client = search_client
        self.dropdown = FileDropDown(results)
        self.back_button = PageBackButton(self)
        query.channel_date_map = results.channel_date_map
        self.next_button = PageNextButton(self)

        if len(results.files) <= 5:
            for file in results.files:
                self.add_item(FileButton(file))
        else:
            self.add_item(self.dropdown)
        self.add_item(self.next_button)

    async def display_current_page(self, interaction: discord.Interaction):
        preview_file = self.pages[self.current_page].files[0]
        embed = self.build_embed(preview_file=preview_file, interaction=interaction)
        self.dropdown = FileDropDown(self.pages[self.current_page])
        self.add_views()
        await interaction.message.edit(embed=embed, view=self)

    async def next_page(self, interaction: discord.Interaction):
        self.current_page += 1
        if self.current_page > len(self.pages):
            embed = self.build_in_progress_embed(interaction)
            await interaction.message.edit(embed=embed)

            search_results = await fsearch(interaction, self.search_client, self.query)
            if not search_results.files:
                self.current_page -= 1
                # add a message to tell the user that there are no more pages!
            else:
                self.pages[self.current_page] = search_results
                self.query.channel_date_map = search_results.channel_date_map
        await self.display_current_page(interaction)

    async def previous_page(self, interaction: discord.Interaction):
        if self.current_page == 0:
            return
        self.current_page -= 1
        await self.display_current_page(interaction)

    def build_in_progress_embed(self, interaction: discord.Interaction) -> discord.Embed:
        message = interaction.message
        embed = message.embeds[0]
        embed.clear_fields()
        embed.set_image(url=None)
        embed.title = f"Gathering files for page {self.current_page}..."
        message_index = embed.footer.text.index("Delivered")
        footer_text = embed.footer.text[message_index:]
        footer_icon_url = embed.footer.icon_url
        embed.set_footer(text=footer_text, icon_url=footer_icon_url)
        return embed

    def build_embed(self, preview_file: SearchResult, interaction: discord.Interaction) -> discord.Embed:
        message = interaction.message
        embed = message.embeds[0]
        if interaction.guild is not None:
            jump_url = f"https://discord.com/channels/{interaction.guild.id}/{preview_file.channel_id}/{preview_file.message_id}"
            media_url = f"https://cdn.discordapp.com/attachments/{preview_file.channel_id}/{preview_file.objectId}/{preview_file.filename}"

        num_files = len(self.pages[self.current_page].files)
        embed.title = f"Found {num_files} file{'s' if num_files > 0 else ''}"
        embed.clear_fields()
        embed.insert_field_at(index=0, name=preview_file.filename[:256], value=jump_url)
        embed.set_image(url=media_url)

        footer_text = embed.footer.text
        index = footer_text.find("Delivered")
        footer_text = footer_text[index:]
        footer_text = f"Page {self.current_page}, {footer_text}"
        embed.set_footer(text=footer_text, icon_url=embed.footer.icon_url)
        return embed

    def add_views(self):
        self.clear_items()
        self.add_item(self.dropdown)
        if self.current_page > 0:
            self.add_item(self.back_button)
        self.add_item(self.next_button)

