import discord
from discord import Interaction
from bot_instance import bot
import vote
from leaderboard import update_leaderboard_message



@bot.tree.command(name="streak", description="Show your or another user's current win streak.")
async def streak(interaction: Interaction, user: discord.Member = None):
    import os, json
    user = user or interaction.user
    history_file = "match_history.json"
    if not os.path.exists(history_file):
        await interaction.response.send_message("No match history found.", ephemeral=True)
        return
    with open(history_file, "r", encoding="utf-8") as f:
        matches = json.load(f)
    # Only consider finished/forced matches
    user_matches = [m for m in matches if m.get("status") in ("finished", "forced") and any(str(p["id"]) == str(user.id) for p in m.get("players", []))]
    # Sort by date descending
    user_matches.sort(key=lambda m: m.get("date", ""), reverse=True)
    streak = 0
    uid_str = str(user.id)
    for m in user_matches:
        winner_id = m.get("winner")
        pids = [str(p["id"]) for p in m.get("players", [])]
        if winner_id is None:
            # Detecta ganador por score si existe
            score = m.get("score")
            if score and pids:
                try:
                    s1, s2 = [int(x) for x in score.split("-")]
                    if s1 > s2:
                        winner_id = pids[0]
                    elif s2 > s1:
                        winner_id = pids[1]
                except:
                    winner_id = None
        if str(winner_id) == uid_str:
            streak += 1
        else:
            break
    embed = discord.Embed(title=f"Current Win Streak for {user.display_name}", description=f"🏆 {streak} wins in a row", color=0xFFD700 if streak > 0 else 0x00bfff)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="setpingrole", description="Set the role to be pinged for 1v1 queue (admin only)")
async def setpingrole(interaction: Interaction, role: discord.Role):
    if not interaction.user.guild_permissions.administrator:
        embed = discord.Embed(title="Permission Denied", description="You don't have Admin Permissions", color=0xff0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    import json, os
    config_dir = "guild_configs"
    os.makedirs(config_dir, exist_ok=True)
    config_path = os.path.join(config_dir, f"{interaction.guild.id}.json")
    config = {}
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            config = json.load(f)
    config["ping_role_id"] = role.id
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    embed = discord.Embed(title="Ping Role Set", description=f"Rol to ping configured: {role.mention}", color=0x00ff00)
    await interaction.response.send_message(embed=embed, ephemeral=True)
@bot.tree.command(name="sendleaderboard", description="Sends Leaderboard to the Leaderboard channel (admin only)")
async def sendleaderboard(interaction: Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Only Admins can use this command", ephemeral=True)
        return
    # Ejecuta la función de leaderboard.py para enviar/editar el mensaje en el canal
    send_or_edit = update_leaderboard_message(interaction.guild)
    await send_or_edit()
    await interaction.response.send_message("Leaderboard sent/updated in the Leaderboard channel.", ephemeral=True)
import discord
from discord import Interaction
from game_queue import current_queue
from bot_instance import bot
from discord.ui import View, Button


@bot.tree.command(name="queue", description="View the current 1v1 queue.")
async def queue(interaction: Interaction):
    if not current_queue:
        embed = discord.Embed(title="1v1 Queue", description="The queue is empty!", color=0xffcc00)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    desc = "\n".join([f"{idx+1}. {p.mention}" for idx, p in enumerate(current_queue)])
    embed = discord.Embed(title="1v1 Queue", description=f"**Current queue:**\n{desc}", color=0x00ff00)
    await interaction.response.send_message(embed=embed, ephemeral=True)



@bot.tree.command(name="setlogchannel", description="Set the log channel for match results (admin only)")
async def setlogchannel(interaction: Interaction, channel: discord.TextChannel):
    if not interaction.user.guild_permissions.administrator:
        embed = discord.Embed(title="Permission Denied", description="You do not have administrator permissions.", color=0xff0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    # Save the log channel ID to a config file per guild
    import json, os
    config_dir = "guild_configs"
    os.makedirs(config_dir, exist_ok=True)
    config_path = os.path.join(config_dir, f"{interaction.guild.id}.json")
    config = {}
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            config = json.load(f)
    config["log_channel_id"] = channel.id
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    embed = discord.Embed(title="Log Channel Set", description=f"Log channel set to {channel.mention}.", color=0x00ff00)
    await interaction.response.send_message(embed=embed, ephemeral=True)

class LeaderboardView(View):
    def __init__(self, pages, current_page, tank_category, interaction_user):
        super().__init__(timeout=60)
        self.pages = pages
        self.current_page = current_page
        self.tank_category = tank_category
        self.interaction_user = interaction_user
        # No add_item here, only use @discord.ui.button below

    async def interaction_check(self, interaction):
        # Solo el usuario que ejecutó el comando puede usar los botones
        return interaction.user.id == self.interaction_user.id

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

    @discord.ui.button(label="⏪", style=discord.ButtonStyle.secondary, custom_id="first")
    async def first(self, interaction: discord.Interaction, button: Button):
        await self.show_page(interaction, 0)

    @discord.ui.button(label="◀️", style=discord.ButtonStyle.secondary, custom_id="prev")
    async def prev(self, interaction: discord.Interaction, button: Button):
        await self.show_page(interaction, max(0, self.current_page - 1))

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.secondary, custom_id="next")
    async def next(self, interaction: discord.Interaction, button: Button):
        await self.show_page(interaction, min(len(self.pages) - 1, self.current_page + 1))

    @discord.ui.button(label="⏩", style=discord.ButtonStyle.secondary, custom_id="last")
    async def last(self, interaction: discord.Interaction, button: Button):
        await self.show_page(interaction, len(self.pages) - 1)

    async def show_page(self, interaction, page_num):
        self.current_page = page_num
        embed = self.pages[page_num]
        await interaction.response.edit_message(embed=embed, view=self)


@bot.tree.command(name="help", description="Show help for the 1v1 bot.")
async def help_command(interaction: Interaction):
    help_text = (
        "**User Commands:**\n"
        "/queue - View the current queue.\n"
        "/profile [user] - Show your or another user's stats.\n"
        "/leaderboard - View the leaderboard with pagination and tank filter.\n"
        "/history [user] - View your or another user's match history.\n"
        "\n**Admin Commands:**\n"
        "/sendleaderboard - Send/update the leaderboard in the configured channel.\n"
        "/cancelmatch - Cancel an active match and delete its channel.\n"
        "/clearqueue - Clear the waiting queue.\n"
        "/forcematch - Force the result of a match.\n"
        "/activematches - Show active matches.\n"
        "/restartvote - Restart mode voting.\n"
        "/deletematch - Delete a match from history by index.\n"
        "/setlogchannel - Set the log channel.\n"
        "/setqueuechannel - Set the queue channel.\n"
        "/setleaderboardchannel - Set the leaderboard channel.\n"
        "\n**Features:**\n"
        "- All voting and match flows are robust and restricted to match players.\n"
        "- Leaderboard supports pagination, tank filter, and manual refresh.\n"
        "- Error and audit logs are sent to the log channel.\n"
        "- Visuals are polished with colors, emojis, and clear formatting.\n"
        "\n**Examples:**\n"
        "- `/queue`\n"
        "- `/profile @User`\n"
        "- `/leaderboard`\n"
        "- `/history @User`\n"
        "- `/sendleaderboard` (admin only)\n"
        "\nTo use admin commands you need administrator permissions."
    )
    embed = discord.Embed(title="1v1 Bot Help", description=help_text, color=0x00bfff)
    embed.set_thumbnail(url=interaction.guild.me.display_avatar.url if interaction.guild and interaction.guild.me else discord.Embed.Empty)
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="profile", description="Show the 1v1 profile of a player (ELO, stats, etc).")
async def profile(interaction: Interaction, player: discord.Member = None):
    import os, json
    from elo import load_elo
    player = player or interaction.user
    # ELO
    elo_data = load_elo()
    elo = elo_data.get(str(player.id), 1000)
    # Stats
    matches_played = 0
    wins = 0
    losses = 0
    streak = 0
    history_file = "match_history.json"
    if os.path.exists(history_file):
        with open(history_file, "r", encoding="utf-8") as f:
            history = json.load(f)
        pid_str = str(player.id)
        for match in history:
            # Solo partidas terminadas
            if match.get("status") in ("finished", "forced") and "players" in match:
                pids = [str(p["id"]) for p in match["players"]]
                if pid_str in pids:
                    matches_played += 1
                    winner = match.get("winner")
                    if winner is None:
                        # Detecta ganador por score si existe
                        score = match.get("score")
                        if score:
                            try:
                                s1, s2 = [int(x) for x in score.split("-")]
                                if s1 > s2:
                                    winner = pids[0]
                                elif s2 > s1:
                                    winner = pids[1]
                            except:
                                winner = None
                    if str(winner) == pid_str:
                        wins += 1
                    elif winner in pids:
                        losses += 1
    winrate = (wins / matches_played * 100) if matches_played > 0 else 0

    user_matches = [match for match in history if match.get("status") in ("finished", "forced") and any(str(p["id"]) == str(player.id) for p in match.get("players", []))]
    user_matches.sort(key=lambda match: match.get("date", ""), reverse=True)
    uid_str = str(player.id)

    for match in user_matches:
        winner_id = match.get("winner")
        pids = [str(p["id"]) for p in match.get("players", [])]
        if winner_id is None:
            # Detecta ganador por score si existe
            score = match.get("score")
            if score and pids:
                try:
                    s1, s2 = [int(x) for x in score.split("-")]
                    if s1 > s2:
                        winner_id = pids[0]
                    elif s2 > s1:
                        winner_id = pids[1]
                except:
                    winner_id = None
        if str(winner_id) == uid_str:
            streak += 1
        else:
            break

    embed = discord.Embed(
        title=f"1v1 Profile: {player.display_name}",
        color=0x00bfff
    )
    embed.add_field(name="ELO", value=str(elo), inline=True)
    embed.add_field(name="Matches Played", value=str(matches_played), inline=True)
    embed.add_field(name="Wins", value=str(wins), inline=True)
    embed.add_field(name="Losses", value=str(losses), inline=True)
    embed.add_field(name="Streak", value=str(streak), inline=True)
    embed.add_field(name="Winrate", value=f"{winrate:.1f}%", inline=True)
    embed.set_thumbnail(url=player.display_avatar.url)
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="leaderboard", description="Show the 1v1 leaderboard (ELO, wins/losses) with pagination and tank filter.")
async def leaderboard(interaction: Interaction):
    from leaderboard import make_leaderboard_pages, LeaderboardTankView
    from elo import load_elo
    history_file = "match_history.json"
    elo_data = load_elo()
    pages_by_tank, tank_names = make_leaderboard_pages(history_file, elo_data)
    view = LeaderboardTankView(pages_by_tank, tank_names)
    embed = pages_by_tank["all"][0]
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
@bot.tree.command(name="senddm", description="Enviar un mensaje privado a un usuario (admin only)")
async def senddm(interaction: Interaction, user: discord.Member, message: str):
    if not interaction.user.guild_permissions.administrator:
        embed = discord.Embed(title="Permission Denied", description="No tienes permisos de administrador.", color=0xff0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    response_sent = False
    try:
        await user.send(message)
        await interaction.response.send_message(f"Mensaje enviado a {user.mention}.", ephemeral=True)
        response_sent = True
    except Exception as e:
        if not response_sent and not interaction.response.is_done():
            await interaction.response.send_message(f"No se pudo enviar el mensaje a {user.mention}. Error: {e}", ephemeral=True)
        elif not response_sent:
            await interaction.followup.send(f"No se pudo enviar el mensaje a {user.mention}. Error: {e}", ephemeral=True)

import random
from constants import TANK_EMOJIS

@bot.tree.command(name="randomtank", description="Get a random tank suggestion for 1v1.")
async def randomtank(interaction: Interaction):
    tanks = list(TANK_EMOJIS.keys())
    tank = random.choice(tanks)
    emoji = TANK_EMOJIS.get(tank, "")
    embed = discord.Embed(title="Random Tank Suggestion", description=f"{emoji} **{tank}**", color=0x00ff00)
    await interaction.response.send_message(embed=embed, ephemeral=True)
def setup(bot):
    tree = bot.tree

    @tree.command(name="1v1unban", description="Unban a user from 1v1s (mod only)")
    async def unban_1v1(interaction: Interaction, user: discord.Member):
        if not is_mod(interaction):
            await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
            return
        import json, os
        config_path = os.path.join("guild_configs", f"{interaction.guild.id}.json")
        config = {}
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                config = json.load(f)
        bans = config.get("banned_users", {})
        if str(user.id) in bans:
            bans.pop(str(user.id))
            config["banned_users"] = bans
            with open(config_path, "w") as f:
                json.dump(config, f, indent=2)
            await interaction.response.send_message(f"{user.mention} has been unbanned from 1v1s.", ephemeral=True)
        else:
            await interaction.response.send_message(f"{user.mention} is not banned.", ephemeral=True)


    @tree.command(name="setmodrole", description="Set the moderator role for 1v1 moderation (admin only)")
    async def setmodrole(interaction: Interaction, role: discord.Role):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You do not have administrator permissions.", ephemeral=True)
            return
        import json, os
        config_dir = "guild_configs"
        os.makedirs(config_dir, exist_ok=True)
        config_path = os.path.join(config_dir, f"{interaction.guild.id}.json")
        config = {}
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                config = json.load(f)
        config["mod_role_id"] = role.id
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        await interaction.response.send_message(f"Moderator role set to {role.mention}.", ephemeral=True)

    def is_mod(interaction):
        import json, os
        config_path = os.path.join("guild_configs", f"{interaction.guild.id}.json")
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                config = json.load(f)
            mod_role_id = config.get("mod_role_id")
            if mod_role_id and any(r.id == mod_role_id for r in interaction.user.roles):
                return True
        return interaction.user.guild_permissions.administrator

    @tree.command(name="1v1ban", description="Ban a user from 1v1s (mod only)")
    async def ban_1v1(interaction: Interaction, user: discord.Member, reason: str = "No reason provided"):
        if not is_mod(interaction):
            await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
            return
        import json, os
        config_path = os.path.join("guild_configs", f"{interaction.guild.id}.json")
        config = {}
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                config = json.load(f)
        bans = config.get("banned_users", {})
        bans[str(user.id)] = reason
        config["banned_users"] = bans
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        await interaction.response.send_message(f"{user.mention} has been banned from 1v1s. Reason: {reason}", ephemeral=True)
    @tree.command(name="history", description="View your or another user's match history.")
    async def history(interaction: Interaction, user: discord.Member = None):
        import os, json
        user = user or interaction.user
        history_file = "match_history.json"
        if not os.path.exists(history_file):
            await interaction.response.send_message("No match history found.", ephemeral=True)
            return
        with open(history_file, "r", encoding="utf-8") as f:
            matches = json.load(f)
        user_matches = [m for m in matches if any(p["id"] == user.id for p in m.get("players", []))]
        if not user_matches:
            await interaction.response.send_message(f"No matches found for {user.mention}.", ephemeral=True)
            return
        embed = discord.Embed(title=f"Match History for {user.display_name}", color=0x3498db)
        # Show up to 10 most recent matches
        for m in user_matches[-10:][::-1]:
            tank = m.get("tank", "?")
            rounds = m.get("rounds", "?")
            score = m.get("score", "?")
            winner_id = m.get("winner")
            winner = f"<@{winner_id}>" if winner_id else "?"
            # Format date
            date = m.get("date", "?")
            # Show both players
            players_str = " vs ".join([f"<@{p['id']}>" for p in m.get("players", [])])
            # Tank emoji
            from constants import TANK_EMOJIS
            tank_emoji = TANK_EMOJIS.get(str(tank), "")
            embed.add_field(
                name=f"{date}",
                value=(
                    f"Players: {players_str}\n"
                    f"Tank: {tank_emoji} {tank}\n"
                    f"Rounds: {rounds}\n"
                    f"Score: {score}\n"
                    f"Winner: {winner}"
                ),
                inline=False
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)