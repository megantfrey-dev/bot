# admin_commands.py
"""
Comandos de administración para el bot de 1v1.
Solo pueden ser usados por administradores.
"""
import discord
from discord import Interaction
from game_queue import update_queue_message, current_queue
from vote import matches, save_active_matches, save_match_to_history
from bot_instance import bot
import os
import json

def is_admin(interaction: Interaction):
    return interaction.user.guild_permissions.administrator

@bot.tree.command(name="cancelmatch", description="Cancel an active match by its index and delete its channel.")
async def cancelmatch(interaction: Interaction, match_id: int):
    if not is_admin(interaction):
        embed = discord.Embed(title="Permission Denied", description="You do not have administrator permissions.", color=0xff0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    active = [m for m in matches if m.get("status") == "active"]
    if match_id < 0 or match_id >= len(active):
        embed = discord.Embed(title="Invalid Index", description="Invalid match index.", color=0xffcc00)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    match = active[match_id]
    channel = interaction.guild.get_channel(match["channel_id"])
    channel_deleted = False
    if channel:
        try:
            embed = discord.Embed(title="Match Cancelled", description="Match cancelled by an administrator.", color=0xff0000)
            await channel.send(embed=embed)
            await channel.delete()
            channel_deleted = True
        except Exception as e:
            # Si falla, igual continúa y cancela el match
            pass
    # Si el canal no existe o ya fue borrado, igual cancela el match y responde sin error
    match["status"] = "cancelled"
    save_match_to_history(match)
    save_active_matches()
    embed = discord.Embed(title="Match Cancelled", description="Match cancelled and saved to history." + (" (Channel not found)" if not channel or not channel_deleted else ""), color=0x00ff00)
    try:
        if not interaction.response.is_done():
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception:
        pass

@bot.tree.command(name="clearqueue", description="Clear the player queue.")
async def clearqueue(interaction: Interaction):
    if not is_admin(interaction):
        embed = discord.Embed(title="Permission Denied", description="You do not have administrator permissions.", color=0xff0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    global current_queue
    current_queue.clear()
    await update_queue_message(interaction.guild)
    embed = discord.Embed(title="Queue Cleared", description="Queue cleared by an administrator.", color=0x00ff00)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="forcematch", description="Force the result of a match.")
async def forcematch(interaction: Interaction, player1: discord.Member, player2: discord.Member, score: str, winner: discord.Member):
    if not is_admin(interaction):
        embed = discord.Embed(title="Permission Denied", description="You do not have administrator permissions.", color=0xff0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    # Cambia p.id por p["id"] porque los jugadores son dicts
    match = next((m for m in matches if set([p["id"] for p in m["players"]]) == set([player1.id, player2.id]) and m.get("status") == "active"), None)
    if not match:
        embed = discord.Embed(title="No Active Match", description="No active match found between those players.", color=0xffcc00)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    match["score"] = score
    match["winner"] = winner.id
    match["status"] = "forced"
    save_match_to_history(match)
    save_active_matches()
    try:
        canal = match.get("channel")
        if canal:
            await canal.send(f":warning: Result forced by admin: {score}, winner: {winner.mention}")
            await canal.delete()
    except Exception:
        pass
    embed = discord.Embed(title="Result Forced", description="Forced result and match saved to history.", color=0x00ff00)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="activematches", description="Show active matches.")
async def activematches(interaction: Interaction):
    if not is_admin(interaction):
        embed = discord.Embed(title="Permission Denied", description="You do not have administrator permissions.", color=0xff0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    active = [m for m in matches if m.get("status") == "active"]
    if not active:
        embed = discord.Embed(title="No Active Matches", description="There are no active matches.", color=0xffcc00)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    msg = "Active matches:\n"
    for idx, m in enumerate(active):
        players = ", ".join([p.name if hasattr(p, "name") else p["name"] for p in m["players"]])
        msg += f"ID: `{idx}` | Channel: <#{m['channel_id']}> | Players: {players}\n"
    embed = discord.Embed(title="Active Matches", description=msg, color=0x00bfff)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="restartvote", description="Restart the mode voting in a match.")
async def restartvote(interaction: Interaction):
    if not is_admin(interaction):
        embed = discord.Embed(title="Permission Denied", description="You do not have administrator permissions.", color=0xff0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    canal = interaction.channel
    match = next((m for m in matches if m.get("channel_id") == canal.id and m.get("status") == "active"), None)
    if not match:
        embed = discord.Embed(title="No Active Match", description="No active match found in this channel.", color=0xffcc00)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    match["current_step"] = "tank"
    match["votes"] = {}
    save_active_matches()
    embed1 = discord.Embed(title="Voting Restarted", description="Voting restarted by admin. Mode selection starts again.", color=0x00bfff)
    await canal.send(embed=embed1)
    embed2 = discord.Embed(title="Voting Restarted", description="Voting restarted.", color=0x00ff00)
    await interaction.response.send_message(embed=embed2, ephemeral=True)

@bot.tree.command(name="deletematch", description="Delete a match from history by its index.")
async def deletematch(interaction: Interaction, match_id: int):
    if not is_admin(interaction):
        embed = discord.Embed(title="Permission Denied", description="You do not have administrator permissions.", color=0xff0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    history_file = "match_history.json"
    if not os.path.exists(history_file):
        embed = discord.Embed(title="No Match History", description="No match history found.", color=0xffcc00)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    with open(history_file, "r", encoding="utf-8") as f:
        history = json.load(f)
    if match_id < 0 or match_id >= len(history):
        embed = discord.Embed(title="Invalid Index", description="Invalid match index.", color=0xffcc00)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    match = history.pop(match_id)
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)
    embed = discord.Embed(title="Match Deleted", description=f"Match deleted from history: {match}", color=0x00ff00)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="setqueuechannel", description="Set the queue channel for 1v1 (admin only)")
async def setqueuechannel(interaction: Interaction, channel: discord.TextChannel):
    if not is_admin(interaction):
        embed = discord.Embed(title="Permission Denied", description="You do not have administrator permissions.", color=0xff0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    import json, os
    config_dir = "guild_configs"
    os.makedirs(config_dir, exist_ok=True)
    config_path = os.path.join(config_dir, f"{interaction.guild.id}.json")
    config = {}
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    config["queue_channel_id"] = channel.id
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    embed = discord.Embed(title="Queue Channel Set", description=f"Queue channel set to {channel.mention}.", color=0x00ff00)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="setleaderboardchannel", description="Set the leaderboard channel for 1v1 (admin only)")
async def setleaderboardchannel(interaction: Interaction, channel: discord.TextChannel):
    if not is_admin(interaction):
        embed = discord.Embed(title="Permission Denied", description="You do not have administrator permissions.", color=0xff0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    import json, os
    config_dir = "guild_configs"
    os.makedirs(config_dir, exist_ok=True)
    config_path = os.path.join(config_dir, f"{interaction.guild.id}.json")
    config = {}
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    config["leaderboard_channel_id"] = channel.id
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    embed = discord.Embed(title="Leaderboard Channel Set", description=f"Leaderboard channel set to {channel.mention}.", color=0x00ff00)
    await interaction.response.send_message(embed=embed, ephemeral=True)

