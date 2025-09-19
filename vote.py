import os
import json
import re
import asyncio
import discord
from discord.ui import Button, View
from discord.utils import get
import bot_instance

def get_parameters_for_tank(tank):
    param_map = {
        "Octo Tank":   "Octo Tank - 2/2/2/8/6/8/9/5/0/0 - 20x20 - horizontal on edge",
        "Overlord":    "Overlord - 2/2/9/8/6/8/0/7/0/0 - 56x56 - vertical",
        "Annihilator": "Annihilator - 0/0/9/9/6/9/3/6/0/0 - 32x32 - vertical",
        "Fighter":     "Fighter - 2/2/2/8/6/8/9/5/0/0 - 56x56 - horizontal",
        "Sniper":      "Sniper - 0/0/7/8/5/8/5/9/0/0 - 20x20 - horizontal on edge",
        "Spawner":     "Spawner - 2/2/5/8/5/8/6/6/0/0 - 56x56 - horizontal",
        "Other": "other",
        "all": "all"
    }
    return param_map.get(tank, None)

# ----------------- SEND VOTE MESSAGE -----------------
async def send_vote_message(match, step):
    players = match["players"]
    # Prevent double sending for the same step
    if match.get("vote_sent", False) and match.get("current_step") == step:
        return
    match["current_step"] = step
    match["vote_sent"] = False
    match["votes"] = {}  # Clear votes for this step

    match_tank = match.get("tank")
    param_str = get_parameters_for_tank(match_tank)

    if step == "tank":
        # Reset config_sent so config embed is only sent after tank vote
        match["config_sent"] = False
        votes = match.get("votes", {})
        players = match["players"]
        vote_status = "\n".join([
            f"{p['mention'] if 'mention' in p else p['name']}: {votes.get(p['id'], 'No vote')}"
            for p in players
        ])
        desc = (
            "🎮 **Select your tank! Both must agree.**\n\n" + vote_status
        )
        options = ["Overlord", "Sniper", "Fighter", "Annihilator", "Octo Tank", "Spawner", "Other"]
    elif step == "region":
        desc = "🌍 **Select your region! Both must agree.**"
        options = ["US West", "US Central", "Europe", "Asia", "Oceania"]
    elif step == "rounds":
        desc = "🔢 **Select number of rounds! Both must agree.**"
        options = ["5", "7", "10", "15"]
    elif step == "score":
        p1, p2 = players
        desc = (
            f"⚔️ **{param_str}**\n"
            "\n"
            "📝 **Type the score in chat when round concludes (format X-Y).**\n"
            f"**Left:** {p1['mention'] if isinstance(p1, dict) else p1.mention}\n"
            f"**Right:** {p2['mention'] if isinstance(p2, dict) else p2.mention}\n"
            "Example: `5-2` (Left = first player, Right = second player)"
        )
        options = None

    embed = discord.Embed(title=f"1v1 {step.capitalize()} Vote", description=desc, color=0x00ff00)
    bot = bot_instance.bot
    channel = bot.get_channel(match["channel_id"])
    if not channel:
        for g in bot.guilds:
            channel = g.get_channel(match["channel_id"])
            if channel:
                break
    if not channel:
        raise RuntimeError(f"Could not find channel with id {match['channel_id']}")

    if options:
        view = VoteView(match, step, options)
        msg = await channel.send(embed=embed, view=view)
    else:
        view = None
        msg = await channel.send(embed=embed)

    match["messages"].append(msg.id)
    match["vote_sent"] = True
    if step == "score":
        await asyncio.sleep(2)
        match["vote_sent"] = False  # Allow next step
    # ...existing code...
    # Remove stray indentation and move move_to_next_step into VoteView class below
import os
import json
import discord
from discord.utils import get
from discord.ui import View, Button
import asyncio
import os
import json
async def start_match(guild, queue):
    """
    Starts a new 1v1 match: creates a channel, sets up match dict, persists, and starts voting.
    queue: list of two discord.Member objects
    """
    # Create a new text channel for the match
    category = get(guild.categories, name="1v1 Matches")
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
    }
    for player in queue:
        overwrites[player] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
    channel = await guild.create_text_channel(
        name=f"1v1-{queue[0].display_name}-vs-{queue[1].display_name}",
        overwrites=overwrites,
        category=category
    )
    # Build match dict
    match = {
        "channel_id": channel.id,
        # Do NOT store the channel object itself, only the ID
        "players": [
            {"id": queue[0].id, "name": queue[0].display_name, "mention": queue[0].mention},
            {"id": queue[1].id, "name": queue[1].display_name, "mention": queue[1].mention}
        ],
        "tank": None,
        "rounds": None,
        "date": str(discord.utils.utcnow()),
        "results": [],
        "current_step": "tank",
        "status": "active",
        # Only store serializable info; do not store message or channel objects
        "messages": [],
        "votes": {},
        "vote_sent": False
    }
    matches.append(match)
    save_active_matches()

    # Send updated rules as embed
    rules_embed = discord.Embed(
        title=":crossed_swords: God Clan 1v1 Format Information",
        color=0x3498db
    )
    rules_embed.add_field(
        name=":book: Basic Rules",
        value=(
            "1 round = 1 life. No resets or commands during fight.\n"
            "Same tank/build must be used.\n"
            "Start = both spin. (rotate in circles to signal readiness). If the enemy tank is off screen (likely droners), use repeal (right  click)\n"
            "Droners must refresh with wall (x) before each round.\n"
            "Lag issues require video proof."
        ),
        inline=False
    )
    rules_embed.add_field(
        name=":no_entry_sign: Forbidden",
        value=(
            "Scripts, macros, command/stat abuse (e.g. FOV).\n"
            "Region conflict? One round per region or use neutral server.\n"
            "If we discover faked or staged 1v1s, you’ll be punished."
        ),
        inline=False
    )
    rules_embed.add_field(
        name="How to 1v1",
        value=(
            "Join the queue, the 1v1 channel will be made.\n"
            "Vote the tank, region, rounds.\n"
            "1v1 the determinated amount of rounds in arras sandbox server.\n"
            "After the 1v1 is finished, send the score here.\n"
            "Remember to ask staffs for help if you have any doubt.\n"
        ),
        inline=False
    )
    await channel.send(f"Welcome {queue[0].mention} and {queue[1].mention} to your 1v1 channel!")
    await channel.send(embed=rules_embed)

    # Start the voting process
    await send_vote_message(match, "tank")
    # Vacía la cola después de crear la partida
    from game_queue import current_queue
    current_queue.clear()
    # Remove players from queue (should be done by caller)

import os
import json
# --- SCORE VOTE CHAT DETECTION ---
###########################
# MATCHES PERSISTENCE API #
###########################

# Path constants
ACTIVE_MATCHES_PATH = os.path.join(os.path.dirname(__file__), 'active_matches.json')
MATCH_HISTORY_PATH = os.path.join(os.path.dirname(__file__), 'match_history.json')

# Load active matches at startup
try:
    with open(ACTIVE_MATCHES_PATH, 'r', encoding='utf-8') as f:
        matches = json.load(f)
except Exception:
    matches = []

def save_active_matches():
    with open(ACTIVE_MATCHES_PATH, 'w', encoding='utf-8') as f:
        json.dump(matches, f, indent=2, ensure_ascii=False)

def save_match_to_history(match):
    try:
        if os.path.exists(MATCH_HISTORY_PATH):
            with open(MATCH_HISTORY_PATH, 'r', encoding='utf-8') as f:
                history = json.load(f)
        else:
            history = []
    except Exception:
        history = []
    history.append(match)
    with open(MATCH_HISTORY_PATH, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


import re
from discord.ext import commands

# Exported symbols for import
__all__ = ["matches", "save_active_matches", "save_match_to_history", "start_match"]

# Añade un diccionario global para locks por match (por channel_id)
score_approval_locks = {}

# valid_other_tanks = [basic, twin, sniper, machine gun, flank guard, director, pounder, trapper, desmos, smasher, spike, mega smasher, landmine, auto smasher, helix, triplex, quadruplex, builder, tri-trapper, trap guard, barricade, overtrapper, bushwhacker, gunner trapper, bomber, conqueror, bullwark, fortress, hexa trapper, septa trapper, architect, constructor, auto builder, engineer, boomer, assembler, architect, eagle, shotgun, launcher, artillery, destroyer, skimmer, twister, swarmer, sidewinder, field gun, beekeeper, ordnance, mortar, field gun, hybrid, annihilator, overseer, cruiser, underseer, big cheese, manager, spawner, necromancer, maleficitor, infestor, factory, auto spawner, battleship, carrier, auto cruiser, commander, overlord, overtrapper, overgunner, banshee, auto overseer, overdrive, triple twin, auto 3, tri angle, hexa tank, auto 4, auto 5, mega 3, fighter, booster, falcon, surfer, phoenix, vulture, octo tank, cyclone, hexa trapper, gunner, minigun, sprayer, focal, redistributor, atomizer, focal, auto gunner, nailgun, machine gunner, streamliner, crop duster, assassin, hunter, marksman, rifle, deadeye, nimrod, revolver, fork, musket, crossbow, armsman, predator, x hunter, poacher, dual, ranger, stalker, single, auto assasin, double twin, triple shot, penta shot, bent hybrid, triplet, bent double, spreadshot, triple twin, hewn double, auto double]

def setup_tank_listener(bot): #Auriga
    @bot.event
    async def on_message(message):
        if message.author.bot:
            return
        for match in matches:
            # --- Score voting only ---
            if match.get("status") == "active" and match.get("current_step") == "tank" and match.get("awaiting_other_tank") == True:
                if message.channel.id == match["channel_id"]:
                    player_ids = [p['id'] if isinstance(p, dict) else p.id for p in match["players"]]
                    if message.author.id not in player_ids:
                        return

                    match.setdefault("other_tank_votes", {})
                    match["other_tank_votes"][message.author.id] = message.content.strip()

                    p1, p2 = match["players"]
                    v1 = match["other_tank_votes"].get(player_ids[0], None)
                    v2 = match["other_tank_votes"].get(player_ids[1], None)

                    embed = discord.Embed(title="Other Tank Voting", color=0xffcc00)
                    embed.add_field(name="Left", value=f"{p1['mention'] if isinstance(p1, dict) else p1.mention}: {v1 if v1 else 'Not voted'}", inline=True)
                    embed.add_field(name="Right", value=f"{p2['mention'] if isinstance(p2, dict) else p2.mention}: {v2 if v2 else 'Not voted'}", inline=True)

                    if v1 and v2:
                        if v1 == v2:
                            embed.description = "✅ Both players agreed to a tank"
                        else:
                            embed.description = "❌ Tanks do not match. Please both vote again."
                    else:
                        embed.description = "Waiting for both players to submit a tank."

                    bot_user_id = message.guild.me.id if hasattr(message.guild, 'me') else None
                    last_bot_msg = None
                    async for msg in message.channel.history(limit=10):
                        if msg.author.id == bot_user_id and msg.embeds and msg.embeds[0].title == "Other Tank Vote":
                            last_bot_msg = msg
                            break
                    if last_bot_msg:
                        await last_bot_msg.edit(embed=embed)
                    else:
                        await message.channel.send(embed=embed)

                    if v1 and v2 and v1 == v2:
                        await send_vote_message(match, "region")


def setup_score_listener(bot):
    @bot.event
    async def on_message(message):
        if message.author.bot:
            return
        for match in matches:
            # --- Score voting only ---
            if match.get("status") == "active" and match.get("current_step") == "score":
                if message.channel.id == match["channel_id"]:
                    player_ids = [p['id'] if isinstance(p, dict) else p.id for p in match["players"]]
                    if message.author.id not in player_ids:
                        return
                    m = re.match(r"^(\d+)[-:](\d+)$", message.content.strip())
                    if not m:
                        await message.channel.send(f"Invalid score format. Please use X-Y (e.g., 5-3). Only players can submit the score.")
                        return
                    rounds = match.get("rounds")
                    try:
                        rounds_int = int(rounds)
                    except Exception:
                        rounds_int = None
                    if rounds_int not in [5, 7, 10, 15, 20]:
                        await message.channel.send(f"Error: Invalid rounds value for this match. Allowed: 5, 7, 10, 15, 20.")
                        return
                    s1, s2 = int(m.group(1)), int(m.group(2))
                    if s1 + s2 != rounds_int:
                        await message.channel.send(f"Invalid score: The sum of both scores must be equal to the number of rounds ({rounds_int}). Example: For {rounds_int} rounds, valid scores are X-Y where X+Y={rounds_int}.")
                        return
                    match.setdefault("score_votes", {})
                    # Si ya hay dos votos y no coinciden, reinicia la votación
                    if len(match["score_votes"]) == 2 and len(set(match["score_votes"].values())) > 1:
                        match["score_votes"] = {}
                        await message.channel.send("Scores did not match. Please both vote again.")
                    # Registra el voto
                    match["score_votes"][message.author.id] = message.content.strip()
                    # Mostrar embed con el estado actual de los votos
                    p1, p2 = match["players"]
                    v1 = match["score_votes"].get(player_ids[0], None)
                    v2 = match["score_votes"].get(player_ids[1], None)
                    embed = discord.Embed(title="1v1 Score Vote", color=0x00ff00)
                    embed.add_field(name="Left", value=f"{p1['mention'] if isinstance(p1, dict) else p1.mention}: {v1 if v1 else 'Not voted'}", inline=True)
                    embed.add_field(name="Right", value=f"{p2['mention'] if isinstance(p2, dict) else p2.mention}: {v2 if v2 else 'Not voted'}", inline=True)
                    if v1 and v2:
                        if v1 == v2:
                            embed.description = "✅ Both players agreed. Match finished!"
                        else:
                            embed.description = "❌ Scores do not match. Please both vote again."
                    else:
                        embed.description = "Waiting for both players to submit their score."
                    # Busca el último mensaje de score del bot y edítalo, si no, envía uno nuevo
                    bot_user_id = message.guild.me.id if hasattr(message.guild, 'me') else None
                    last_bot_msg = None
                    async for msg in message.channel.history(limit=10):
                        if msg.author.id == bot_user_id and msg.embeds and msg.embeds[0].title == "1v1 Score Vote":
                            last_bot_msg = msg
                            break
                    if last_bot_msg:
                        await last_bot_msg.edit(embed=embed)
                    else:
                        await message.channel.send(embed=embed)
                    # Si ambos votaron y coinciden, termina el match
                    if v1 and v2 and v1 == v2 and not match.get("score_approval_sent"):
                        # Always get tank and rounds from match['tank'] and match['rounds']
                        tank = match.get('tank')
                        rounds = match.get('rounds')
                        # Save score, tank, and rounds to match dict
                        match["score"] = v1
                        match["score_approval_sent"] = True
                        match["status"] = "finished"
                        # ...existing code for winner, ELO, leaderboard, etc...
                        # --- Determine winner ---
                        s1, s2 = [int(x) for x in v1.split('-')]
                        if s1 > s2:
                            winner = match['players'][0]
                            loser = match['players'][1]
                        else:
                            winner = match['players'][1]
                            loser = match['players'][0]
                        # --- Update ELO ---
                        from elo import update_elo
                        # Asegura que los IDs sean string
                        for p in match['players']:
                            if not isinstance(p['id'], str):
                                p['id'] = str(p['id'])
                        score_str = v1
                        update_elo(winner, loser, winner, score_str)
                        print(f"ELO actualizado: {match['players'][0]['id']} vs {match['players'][1]['id']}, ganador: {winner['id']}")
                        # Elimina la match de la lista de activos
                        if match in matches:
                            matches.remove(match)
                            save_active_matches()
                        # --- Save to history ---
                        save_match_to_history(match)
                        # --- Update leaderboard ---
                        try:
                            from leaderboard import update_leaderboard_message
                            bot = bot_instance.bot
                            guild = bot.get_guild(message.guild.id)
                            coro = update_leaderboard_message(guild)
                            if coro:
                                await coro()
                        except Exception as e:
                            print(f"Leaderboard update error: {e}")
                        # --- Send result to logs and queue channels ---
                        import os, json
                        config_path = os.path.join("guild_configs", f"{message.guild.id}.json")
                        log_channel_id = None
                        queue_channel_id = None
                        if os.path.exists(config_path):
                            with open(config_path, "r", encoding="utf-8") as f:
                                config = json.load(f)
                            log_channel_id = config.get("log_channel_id")
                            queue_channel_id = config.get("queue_channel_id")
                        # --- Calcula y muestra el cambio de ELO ---
                        from elo import load_elo, K_FACTOR
                        # Get previous ELOs before update
                        elo_data_before = load_elo()
                        p1_id = match['players'][0]['id']
                        p2_id = match['players'][1]['id']
                        p1_old = elo_data_before.get(str(p1_id), 1000)
                        p2_old = elo_data_before.get(str(p2_id), 1000)
                        # Update ELOs
                        from elo import update_elo
                        score_str = v1
                        update_elo(winner, loser, winner, score_str)
                        elo_data_after = load_elo()
                        p1_new = elo_data_after.get(str(p1_id), 1000)
                        p2_new = elo_data_after.get(str(p2_id), 1000)
                        p1_delta = p1_new - p1_old
                        p2_delta = p2_new - p2_old
                        result_embed = discord.Embed(title="1v1 Match Result", color=0xFFD700)
                        result_embed.add_field(name="Players", value=f"{match['players'][0]['mention']} vs {match['players'][1]['mention']}", inline=False)
                        # Only show tank name in result embed
                        result_embed.add_field(name="Tank", value=match.get('tank', 'N/A'), inline=True)
                        result_embed.add_field(name="Region", value=match.get('region', 'N/A'), inline=True)
                        result_embed.add_field(name="Rounds", value=str(match.get('rounds', 'N/A')), inline=True)
                        result_embed.add_field(name="Score", value=v1, inline=True)
                        result_embed.add_field(name="Winner", value=winner['mention'], inline=True)
                        result_embed.add_field(
                            name=f"{match['players'][0]['name']} ELO",
                            value=f"{p1_old} → {p1_new} ({'+' if p1_delta >= 0 else ''}{p1_delta})",
                            inline=True
                        )
                        result_embed.add_field(
                            name=f"{match['players'][1]['name']} ELO",
                            value=f"{p2_old} → {p2_new} ({'+' if p2_delta >= 0 else ''}{p2_delta})",
                            inline=True
                        )
                        # Send to logs channel
                        bot = bot_instance.bot
                        if log_channel_id:
                            log_channel = bot.get_channel(log_channel_id)
                            if log_channel:
                                await log_channel.send(embed=result_embed)
                        # Send to queue channel
                        if queue_channel_id:
                            queue_channel = bot.get_channel(queue_channel_id)
                            if queue_channel:
                                await queue_channel.send(embed=result_embed)
                        # --- Delete match channel ---
                        try:
                            match_channel = bot.get_channel(match['channel_id'])
                            if match_channel:
                                await match_channel.delete(reason="Match finished and agreed by both players.")
                        except Exception as e:
                            print(f"Error deleting match channel: {e}")



# ----------------- VOTE VIEW CLASS -----------------

from discord.ui import Button, View

# ----------------- VOTE VIEW CLASS -----------------
class VoteView(View):
    async def move_to_next_step(self):
        # Advance to the next voting step
        if self.step == "tank":
            await send_vote_message(self.match, "region")
        elif self.step == "region":
            await send_vote_message(self.match, "rounds")
        elif self.step == "rounds":
            await send_vote_message(self.match, "score")
    def __init__(self, match, step, options):
        super().__init__(timeout=None)
        self.match = match
        self.step = step
        self.options = options
        self.buttons = []
        from constants import TANK_EMOJIS
        import re
        if options:
            region_emojis = {
                "US West": "🇺🇸",
                "US Central": "🇺🇸",
                "Europe": "🇪🇺",
                "Asia": "🌏",
                "Oceania": "🌊"
            }
            for idx, option in enumerate(options):
                row = idx // 5  # Each row can have up to 5 buttons
                emoji_obj = None
                # Si es votación de región, usa emoji custom
                if self.step == "region":
                    emoji = region_emojis.get(option, None)
                    if emoji:
                        emoji_obj = emoji
                elif option == "Other":
                    emoji_obj = "❓"
                else:
                    emoji_str = TANK_EMOJIS.get(option, None)
                    if emoji_str:
                        m = re.match(r"<:([a-zA-Z0-9_]+):(\d+)>", emoji_str)
                        if m:
                            from discord import PartialEmoji
                            emoji_obj = PartialEmoji(name=m.group(1), id=int(m.group(2)))
                button = Button(label=option, style=discord.ButtonStyle.primary, custom_id=f"vote_option_{idx}", row=row, disabled=False, emoji=emoji_obj)
                async def callback(interaction, opt=option):
                    await self.handle_vote(interaction, opt)
                button.callback = callback
                self.add_item(button)
                self.buttons.append(button)

    async def handle_vote(self, interaction, option):
        self.match["votes"][interaction.user.id] = option
        votes = self.match["votes"]
        players = self.match["players"]
        feedback = "\n".join([
            f"{p['mention'] if 'mention' in p else p['name']}: {votes.get(p['id'], 'No vote')}"
            for p in players
        ])
        # --- Tank voting ---
        if self.step == "tank":
            # Solo avanza si ambos han votado
            if len(votes) == len(players):
                if votes[players[0]['id']] == "Other" and votes[players[1]['id']] == "Other":
                    self.match["tank"] = None  # No avanzar aún
                    self.match["awaiting_other_tank"] = True
                    self.match["other_tank_votes"] = {}
                    embed = discord.Embed(title="Other Tank Selected", description="Both players must type the tank name in chat. The bot will continue when both have typed the same name.", color=0xffcc00)
                    await interaction.channel.send(embed=embed)
                elif len(set(votes.values())) == 1:
                    # Ambos votaron el mismo tanque normal
                    selected_tank = list(votes.values())[0]
                    self.match["tank"] = selected_tank
                    self.match["awaiting_other_tank"] = False
                    self.match["other_tank_votes"] = {}
                    # (embed de configuración eliminado)
                    await self.move_to_next_step()
                    # Disable all buttons for this step after voting is complete
                    for btn in self.buttons:
                        btn.disabled = True
                    await interaction.message.edit(view=self)
            else:
                # Disagreement: allow re-vote, show feedback
                await interaction.channel.send("No agreement reached on tank. Try using `/randomtank` for a suggestion!")
                # Do NOT disable buttons, allow re-vote
                # Update embed to show current votes
                if self.match["messages"]:
                    import bot_instance
                    bot = bot_instance.bot
                    channel = bot.get_channel(self.match["channel_id"])
                    if not channel:
                        for g in bot.guilds:
                            channel = g.get_channel(self.match["channel_id"])
                            if channel:
                                break
                    if channel:
                        last_msg_id = self.match["messages"][-1]
                        try:
                            last_msg = await channel.fetch_message(last_msg_id)
                            embed = last_msg.embeds[0] if last_msg.embeds else None
                            if embed:
                                embed.description = f"{self.step.capitalize()} voting in progress.\n\n" + feedback
                                await last_msg.edit(embed=embed)
                        except Exception:
                            pass
        # --- Region voting ---
        if self.step == "region":
            # Always show current votes after any vote
            if self.match["messages"]:
                import bot_instance
                bot = bot_instance.bot
                channel = bot.get_channel(self.match["channel_id"])
                if not channel:
                    for g in bot.guilds:
                        channel = g.get_channel(self.match["channel_id"])
                        if channel:
                            break
                if channel:
                    last_msg_id = self.match["messages"][-1]
                    try:
                        last_msg = await channel.fetch_message(last_msg_id)
                        embed = last_msg.embeds[0] if last_msg.embeds else None
                        if embed:
                            embed.description = f"{self.step.capitalize()} voting in progress.\n\n" + feedback
                            await last_msg.edit(embed=embed)
                    except Exception:
                        pass
            # If both have voted
            if len(votes) == len(players):
                if len(set(votes.values())) == 1:
                    self.match["region"] = list(votes.values())[0]
                    await self.move_to_next_step()
                    # Disable all buttons for this step after voting is complete
                    for btn in self.buttons:
                        btn.disabled = True
                    await interaction.message.edit(view=self)
                else:
                    # Disagreement: allow re-vote, show feedback
                    await interaction.channel.send("No agreement reached on region. Please vote again.")
                    # Do NOT disable buttons, allow re-vote
        # --- Rounds voting ---
        if self.step == "rounds":
            # Always show current votes after any vote
            if self.match["messages"]:
                import bot_instance
                bot = bot_instance.bot
                channel = bot.get_channel(self.match["channel_id"])
                if not channel:
                    for g in bot.guilds:
                        channel = g.get_channel(self.match["channel_id"])
                        if channel:
                            break
                if channel:
                    last_msg_id = self.match["messages"][-1]
                    try:
                        last_msg = await channel.fetch_message(last_msg_id)
                        embed = last_msg.embeds[0] if last_msg.embeds else None
                        if embed:
                            embed.description = f"{self.step.capitalize()} voting in progress.\n\n" + feedback
                            await last_msg.edit(embed=embed)
                    except Exception:
                        pass
            # If both have voted
            if len(votes) == len(players):
                if len(set(votes.values())) == 1:
                    try:
                        self.match["rounds"] = int(list(votes.values())[0])
                    except Exception:
                        self.match["rounds"] = list(votes.values())[0]
                    for btn in self.buttons:
                        btn.disabled = True
                    await interaction.message.edit(view=self)
                    await self.move_to_next_step()
                else:
                    # Only send disagreement message if not already responded
                    if not interaction.response.is_done():
                        await interaction.response.send_message("No agreement reached on rounds. Please vote again.", ephemeral=True)
                    else:
                        await interaction.channel.send("No agreement reached on rounds. Please vote again.")
        # Responde a la interacción para evitar "This interaction failed"
        # Always send feedback as ephemeral (only visible to the user)
        #try:
        #    if not interaction.response.is_done():
        #        await interaction.response.send_message(
        #            f"Your vote for **{getattr(self, 'step', self.match.get('current_step', ''))}**: `{option}` has been registered.\n\nCurrent votes:\n{feedback}",
        #            ephemeral=True
        #        )
        #    else:
        #        await interaction.followup.send(
        #            f"Your vote for **{getattr(self, 'step', self.match.get('current_step', ''))}**: `{option}` has been registered.\n\nCurrent votes:\n{feedback}",
        #            ephemeral=True
        #        )
        #except Exception as e:
        #    print(f"[ERROR] Could not respond to interaction: {e}")
        # Edit the last vote message to show current votes (opcional, si quieres actualizar el embed)
        if self.match["messages"]:
            import bot_instance
            bot = bot_instance.bot
            channel = bot.get_channel(self.match["channel_id"])
            if not channel:
                @bot.event
                async def on_message(message):
                    if message.author.bot:
                        return
                    for match in matches:
                        # --- Other tank chat handling ---
                        if match.get("status") == "active" and match.get("current_step") == "tank" and match.get("awaiting_other_tank"):
                            if message.channel.id == match["channel_id"]:
                                player_ids = [p['id'] if isinstance(p, dict) else p.id for p in match["players"]]
                                if message.author.id not in player_ids:
                                    return
                                # Save tank name per player
                                tank_name = message.content.strip()
                                match["other_tank_votes"][message.author.id] = tank_name
                                # Show current votes
                                votes = match["other_tank_votes"]
                                feedback = "\n".join([
                                    f"{p['mention'] if 'mention' in p else p['name']}: {votes.get(p['id'], 'No vote')}"
                                    for p in match["players"]
                                ])
                                # embed = discord.Embed(title="Other Tank Voting", description=feedback, color=0xffcc00)
                                # await message.channel.send(embed=embed)
                                # If both voted and agree, set tank and continue
                                if len(votes) == 2:
                                    vals = list(votes.values())
                                    if vals[0].strip().lower() == vals[1].strip().lower():
                                        match["tank"] = vals[0].strip()
                                        match["awaiting_other_tank"] = False
                                        await send_vote_message(match, "region")
                                return
                        # --- Score voting ---
                        if match.get("status") == "active" and match.get("current_step") == "score":
                            if message.channel.id == match["channel_id"]:
                                player_ids = [p['id'] if isinstance(p, dict) else p.id for p in match["players"]]
                                if message.author.id not in player_ids:
                                    return
                                m = re.match(r"^(\d+)[-:](\d+)$", message.content.strip())
                                if not m:
                                    await message.channel.send(f"Invalid score format. Please use X-Y (e.g., 5-3). Only players can submit the score.")
                                    return
                                # ...existing code...
