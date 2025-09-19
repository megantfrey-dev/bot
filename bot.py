import os
from dotenv import load_dotenv
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN is None:
    raise ValueError("❌ DISCORD_TOKEN not found! Make sure you have a .env file with DISCORD_TOKEN set.")


from bot_instance import bot
from logger import get_logger
import discord
import json


# Import command modules to register all commands
import slash_commands
slash_commands.setup(bot)
import admin_commands

# Enable score listener for match channels (chat-based score voting)
from vote import setup_score_listener
from vote import setup_tank_listener
setup_score_listener(bot)
setup_tank_listener(bot) #Auriga

logger = get_logger("bot")

async def send_log_channel(guild, message):
	config_path = os.path.join("guild_configs", f"{guild.id}.json")
	if os.path.exists(config_path):
		with open(config_path, "r", encoding="utf-8") as f:
			config = json.load(f)
		log_channel_id = config.get("log_channel_id")
		if log_channel_id:
			channel = guild.get_channel(log_channel_id)
			if channel:
				try:
					await channel.send(message)
				except Exception:
					pass

@bot.event
async def on_ready():
	logger.info(f"✅ Bot connected as {bot.user}")
	from rich_presence import set_rich_presence
	await set_rich_presence(bot)
	from game_queue import update_queue_message, QueueView
	from leaderboard import LeaderboardTankView, make_leaderboard_pages
	# Register persistent views for queue and leaderboard
	bot.add_view(QueueView())
	# For leaderboard, need to build pages and tank list (use empty for registration)
	bot.add_view(LeaderboardTankView({}, []))
	for guild in bot.guilds:
		await send_log_channel(guild, f"✅ Bot connected as {bot.user}")
		# Delete all previous queue messages except score messages
		import os, json
		config_path = os.path.join("guild_configs", f"{guild.id}.json")
		queue_channel_id = None
		if os.path.exists(config_path):
			with open(config_path, "r", encoding="utf-8") as f:
				config = json.load(f)
			queue_channel_id = config.get("queue_channel_id")
		channel = None
		if queue_channel_id:
			channel = guild.get_channel(queue_channel_id)
		if channel:
			async for msg in channel.history(limit=50):
				# Only delete queue messages (title: '1v1 Queue'), not score messages
				if msg.author.id == bot.user.id and msg.embeds:
					embed = msg.embeds[0]
					if embed.title == "1v1 Queue":
						try:
							await msg.delete()
						except Exception:
							pass
		await update_queue_message(guild)
	try:
		synced = await bot.tree.sync()
		logger.info(f"Synced {len(synced)} global slash commands.")
		for guild in bot.guilds:
			await send_log_channel(guild, f"Synced {len(synced)} global slash commands.")
	except Exception as e:
		logger.error(f"Error syncing slash commands: {e}")
		for guild in bot.guilds:
			await send_log_channel(guild, f"Error syncing slash commands: {e}")

bot.run(TOKEN)

