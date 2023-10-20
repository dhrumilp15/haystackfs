import discord
from ..search.search_models import SearchResults, SearchResult


class FileDropDown(discord.ui.Select):
    def __init__(self, files: SearchResults):
        self.value_to_name = {self.build_select_value(file): file.filename for file in files.files}
        options = self.produce_options()
        super().__init__(placeholder="Choose your files here!", options=options)

    @staticmethod
    def build_select_value(file: SearchResult):
        return ','.join(map(str, [file.channel_id, file.message_id, file.objectId]))

    def produce_options(self):
        return [discord.SelectOption(label=name[:25], value=value) for value, name in self.value_to_name.items()]

    async def callback(self, interaction: discord.Interaction):
        # edit the embed here
        value = self.values[0]
        name = self.value_to_name[value]
        message = interaction.message
        embed = message.embeds[0]
        channel_id, message_id, file_id = value.split(',')
        if interaction.guild is not None:
            jump_url = f"https://discord.com/channels/{interaction.guild.id}/{channel_id}/{message_id}"
            media_url = f"https://cdn.discordapp.com/attachments/{channel_id}/{file_id}/{name}"
        embed.set_field_at(index=0, name=name[:256], value=jump_url)
        embed.set_image(url=media_url)
        await interaction.response.edit_message(embed=embed)
