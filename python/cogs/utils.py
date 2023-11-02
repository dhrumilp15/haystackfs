from python.models.query import Query
import discord
from ..exceptions import CommandHandler


def get_command_type(function_name: str):
	command_types = ['search', 'export', 'delete']
	for command_type in command_types:
		if command_type in function_name:
			return command_type
	return "NO COMMAND TYPE DETECTED"


def give_signature(real_func):

	class SimpleClass:

		async def command_function(
			haystack_obj,
			interaction: discord.Interaction,
			*,
			filename: str = None,
			filetype: str = None,
			custom_filetype: str = None,
			author: discord.User = None,
			channel: discord.TextChannel = None,
			content: str = None,
			after: str = None,
			before: str = None,
			dm: bool = False
		):
			await interaction.response.defer()
			query = Query(
				filename=filename,
				filetype=filetype,
				custom_filetype=custom_filetype,
				author=author,
				channel=channel,
				content=content,
				after=after,
				before=before,
				dm=dm
			)
			command_type = get_command_type(real_func.__name__)
			async with CommandHandler(
				interaction=interaction,
				bot=haystack_obj.bot,
				command_type=command_type,
				query=query
			):
				return await real_func(self=haystack_obj, interaction=interaction, query=query)

	return SimpleClass.command_function
