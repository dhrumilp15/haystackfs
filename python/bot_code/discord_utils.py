import discord


async def update_server_count(home_guild: discord.Guild, num_guilds: int):
    if home_guild is None:
        return
    name = f"Server Count: {num_guilds}"
    category = None
    for cat in home_guild.categories:
        if cat.name == "Bot Stats":
            category = cat
            break
    if category is None:
        category = await home_guild.create_category_channel(name="Bot Stats")
        await home_guild.create_voice_channel(name=name, category=category, user_limit=0)
    else:
        channels = category.voice_channels
        edited = False
        for chan in channels:
            if chan.name.startswith("Server Count: "):
                try:
                    await chan.edit(name=name)
                    edited = True
                except:
                    pass
        if not edited:
            try:
                await home_guild.create_voice_channel(name=name, category=category, user_limit=0)
            except:
                pass
