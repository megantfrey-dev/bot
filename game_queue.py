# game_queue.py
import os 
import discord
from discord.ui import View, Button
from elo import load_elo, save_elo

current_queue = []
queue_message = None
queue_starting = False  # Flag para evitar doble partida

# ----------------- ACTUALIZA EL MENSAJE DE LA COLA -----------------
async def update_queue_message(guild):  # Recibimos el 'guild' directamente
    global queue_message
    # Intenta obtener el canal configurado por comando
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
    if not channel:
        # Si no está configurado, busca por nombre (legacy)
        QUEUE_CHANNEL_NAME = "1v1-queue"
        from constants import MATCH_CATEGORY_NAME
        channel = discord.utils.get(guild.text_channels, name=QUEUE_CHANNEL_NAME)
        if not channel:  # Si el canal no existe, lo creamos
            category = discord.utils.get(guild.categories, name=MATCH_CATEGORY_NAME)
            if not category:
                category = await guild.create_category(MATCH_CATEGORY_NAME)
            channel = await guild.create_text_channel(QUEUE_CHANNEL_NAME, category=category)

    # Elimina todos los mensajes anteriores del bot en el canal de la queue
    if channel:
        async for msg in channel.history(limit=20):
            if msg.author == channel.guild.me and msg.embeds and msg.embeds[0].title == "1v1 Queue":
                try:
                    await msg.delete()
                except:
                    pass

    # Crea un nuevo mensaje de embed con la información de la cola
    embed = discord.Embed(title="1v1 Queue", color=0x00ff00)
    if current_queue:
        desc = ""
        for idx, player in enumerate(current_queue, start=1):
            desc += f"{idx}. {player.mention}\n"  # Muestra los jugadores en la cola
        desc += f"\nQueue {len(current_queue)}/2"
        embed.description = desc
    else:
        embed.description = "Queue is empty!\nQueue 0/2"

    queue_message = await channel.send(embed=embed, view=QueueView())  # Envía el mensaje al canal

# ----------------- CLASE QUE MANEJA LOS BOTONES -----------------
class QueueView(View):
    @property
    def persistent(self):
        return True

    @classmethod
    def is_persistent(cls):
        return True
    def __init__(self):
        super().__init__(timeout=0)  # Persistent view
        join_btn = Button(label="Join Queue", style=discord.ButtonStyle.green, custom_id="queue_join")
        leave_btn = Button(label="Leave Queue", style=discord.ButtonStyle.red, custom_id="queue_leave")
        ping_btn = Button(label="Ping Role", style=discord.ButtonStyle.blurple, custom_id="queue_ping")
        join_btn.callback = self.join
        leave_btn.callback = self.leave
        ping_btn.callback = self.ping_role
        self.add_item(join_btn)
        self.add_item(leave_btn)
        self.add_item(ping_btn)

    # Cooldown tracking per guild
    ping_cooldowns = {}  # {guild_id: timestamp}

    async def ping_role(self, interaction: discord.Interaction):
        # Only allow if user is in the queue
        if interaction.user not in current_queue:
            embed = discord.Embed(title="Queue Info", description="You must be in the queue to use this button.", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        import time, json, os
        guild_id = interaction.guild.id
        now = time.time()
        last_ping = self.ping_cooldowns.get(guild_id, 0)
        if now - last_ping < 600:
            remaining = int(600 - (now - last_ping))
            embed = discord.Embed(title="Ping Cooldown", description=f"You must wait {remaining} seconds before pinging again.", color=0xffcc00)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        # Get ping role from config
        config_path = os.path.join("guild_configs", f"{guild_id}.json")
        ping_role_id = None
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            ping_role_id = config.get("ping_role_id")
        if not ping_role_id:
            embed = discord.Embed(title="Ping Role Not Set", description="No ping role configured. Use `/setpingrole`.", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        role = interaction.guild.get_role(ping_role_id)
        if not role:
            embed = discord.Embed(title="Ping Role Not Found", description="The configured role does not exist in this server.", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        # Ping the role in the queue channel
        self.ping_cooldowns[guild_id] = now
        await interaction.channel.send(f"{role.mention} There is a match waiting in the 1v1 queue!")
        embed = discord.Embed(title="Ping sent", description=f"{role.mention} has been pinged.", color=0x00ff00)
        await interaction.response.send_message(embed=embed, ephemeral=True)



    async def join(self, interaction: discord.Interaction):
        global queue_starting, queue_message
        if interaction.user in current_queue:
            embed = discord.Embed(title="Queue Info", description="You are already in the queue!", color=0xffcc00)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Revisar si el usuario está baneado
        import os, json
        config_path = os.path.join("guild_configs", f"{interaction.guild.id}.json")
        banned = set()
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            banned = set(config.get("banned_users", {}).keys())
        if str(interaction.user.id) in banned:
            embed = discord.Embed(title="Queue Info", description="You are banned from 1v1s and cannot join the queue.", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Prevent joining if user is in an active match
        from vote import matches
        user_id = interaction.user.id
        for match in matches:
            if match.get("status") in ("active", "score", "tank", "region", "rounds"):
                for p in match["players"]:
                    pid = p.id if hasattr(p, "id") else p["id"]
                    if pid == user_id:
                        embed = discord.Embed(title="Queue Info", description="You are already in an active 1v1 match and cannot join another queue.", color=0xff0000)
                        await interaction.response.send_message(embed=embed, ephemeral=True)
                        return

        # Evita que más de 2 personas se unan a la queue
        if len(current_queue) >= 2:
            embed = discord.Embed(title="Queue Full", description="The queue is already full (2 players). Please wait for the next match.", color=0xffcc00)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        current_queue.append(interaction.user)
        embed = discord.Embed(title="Queue Info", description="You joined the queue!", color=0x00ff00)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        await update_queue_message(interaction.guild)

        # Solo el primer callback que detecta 2 jugadores inicia la partida
        if len(current_queue) == 2 and not queue_starting:
            queue_starting = True
            from vote import start_match
            await start_match(interaction.guild, list(current_queue))
            # Vacía la queue y elimina el mensaje de la queue
            current_queue.clear()
            if queue_message and not getattr(queue_message, "deleted", False):
                try:
                    await queue_message.delete()
                except:
                    pass
            queue_message = None
            await update_queue_message(interaction.guild)
            queue_starting = False


    async def leave(self, interaction: discord.Interaction):
        if interaction.user not in current_queue:
            embed = discord.Embed(title="Queue Info", description="You are not in the queue!", color=0xffcc00)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        current_queue.remove(interaction.user)
        embed = discord.Embed(title="Queue Info", description="You left the queue!", color=0xff0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        await update_queue_message(interaction.guild)

    # Eliminada: la lógica de start_match ahora está en vote.py
