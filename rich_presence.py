import discord

async def set_rich_presence(bot, text="Hosting 1v1 matches"):
    await bot.change_presence(activity=discord.Game(text))
