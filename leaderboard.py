import logging

def debug_button(interaction, custom_id):
    logging.info(f"Botón presionado: {custom_id} por usuario: {interaction.user} (id: {interaction.user.id})")
import discord
import os
import json
from discord.ui import View, Button
from discord import ButtonStyle
from elo import load_elo

class LeaderboardTankView(View):
    def make_tank_callback(self, tank):
        # Normalize tank key to match pages_by_tank keys
        def normalize_tank_key(tank):
            key_map = {
                "Octo Tank": "octo tank",
                "Overlord": "overlord",
                "Annihilator": "annihilator",
                "Fighter": "fighter",
                "Sniper": "sniper",
                "Spawner": "spawner",
                "Other": "other",
                "all": "all"
            }
            return key_map.get(tank, tank.lower())
        async def tank_callback(interaction):
            debug_button(interaction, f"tank_{tank}")
            self.current_tank = normalize_tank_key(tank)
            self.current_page = 0
            # Fallback to 'all' if tank not found
            if self.current_tank not in self.pages_by_tank:
                self.current_tank = "all"
            embed = self.pages_by_tank[self.current_tank][self.current_page]
            if isinstance(embed, list):
                # If it's a list, take the first embed
                embed = embed[0] if embed else None
            await interaction.response.edit_message(embed=embed, view=self)
        return tank_callback
    def __init__(self, pages_by_tank, tank_list):
        super().__init__(timeout=0)  # Persistent view
        # Eliminar solo el botón para 'Itemsex', mantener el resto
        clean_tanks = [t for t in tank_list if t.lower() != "itemsex" and t.lower() != "unknown"]
        self.tank_list = ["all"] + clean_tanks
        self.pages_by_tank = pages_by_tank
        if "all" not in self.pages_by_tank:
            # If 'all' is missing, aggregate all tanks
            all_pages = []
            for tank in self.pages_by_tank:
                all_pages.extend(self.pages_by_tank[tank])
            self.pages_by_tank["all"] = all_pages if all_pages else [[]]
        self.current_tank = "all"
        self.current_page = 0
        self.add_tank_buttons()
    @property
    def persistent(self):
        return True

    @classmethod
    def is_persistent(cls):
        return True
    @discord.ui.button(label="⬅️ Previous", style=discord.ButtonStyle.secondary, custom_id="prev")
    async def prev(self, interaction: discord.Interaction, button: Button):
        debug_button(interaction, "prev")
        self.current_page = max(0, self.current_page - 1)
        await interaction.response.edit_message(embed=self.pages_by_tank[self.current_tank][self.current_page], view=self)

    @discord.ui.button(label="Next ➡️", style=discord.ButtonStyle.secondary, custom_id="next")
    async def next(self, interaction: discord.Interaction, button: Button):
        debug_button(interaction, "next")
        max_page = len(self.pages_by_tank[self.current_tank]) - 1
        self.current_page = min(max_page, self.current_page + 1)
        await interaction.response.edit_message(embed=self.pages_by_tank[self.current_tank][self.current_page], view=self)

    # Tank filter buttons
    def add_tank_buttons(self):
        from constants import TANK_EMOJIS
        import re
        for idx, tank in enumerate(self.tank_list):
            tank_key = tank.title() if tank != "all" else "All"
            emoji_obj = None
            from discord import PartialEmoji
            emoji_str = TANK_EMOJIS.get(tank_key, None)
            if emoji_str:
                m = re.match(r"<:([a-zA-Z0-9_]+):(\d+)>", emoji_str)
                if m:
                    emoji_obj = PartialEmoji(name=m.group(1), id=int(m.group(2)))
            btn_label = tank_key
            btn = Button(label=btn_label, style=ButtonStyle.primary if tank != "all" else ButtonStyle.secondary, emoji=emoji_obj, custom_id=f"tank_{tank_key}")
            btn.callback = self.make_tank_callback(tank_key)
            self.add_item(btn)

    @discord.ui.button(label="Refresh", style=discord.ButtonStyle.success, custom_id="refresh_leaderboard")
    async def refresh_leaderboard(self, interaction: discord.Interaction, button: Button):
        debug_button(interaction, "refresh_leaderboard")
        await interaction.response.defer()
        from leaderboard import update_leaderboard_message
        send_or_edit = update_leaderboard_message(interaction.guild)
        await send_or_edit()

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
    async def interaction_check(self, interaction):
        return True  # Cualquier usuario puede usar los botones

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

    async def on_button_click(self, interaction):
        custom_id = interaction.data["custom_id"]
        max_page = len(self.pages_by_tank[self.current_tank]) - 1
        if custom_id == "prev":
            self.current_page = max(0, self.current_page - 1)
        elif custom_id == "next":
            self.current_page = min(max_page, self.current_page + 1)
        elif custom_id.startswith("tank_"):
            self.current_tank = custom_id[5:]
            self.current_page = 0
        elif custom_id == "refresh_leaderboard":
            from leaderboard import update_leaderboard_message
            send_or_edit = update_leaderboard_message(interaction.guild)
            await send_or_edit()
            return
        self.update_buttons()
        await interaction.response.edit_message(embed=self.pages_by_tank[self.current_tank][self.current_page], view=self)

def make_leaderboard_pages(history_file, elo_data):
    stats_by_tank = {"all": {}}
    tank_names = set()
    known_tanks = ["octo tank", "overlord", "annihilator", "fighter", "sniper", "spawner"]
    if os.path.exists(history_file):
        with open(history_file, "r", encoding="utf-8") as f:
            history = json.load(f)
        for match in history:
            if match.get("status") in ("finished", "forced") and "players" in match and len(match["players"]) == 2:
                match_tank = match.get("tank")
                # Detect custom tank names and add as separate category
                if isinstance(match_tank, dict):
                    match_tank_name = match_tank.get("name", "").strip().lower()
                elif isinstance(match_tank, str):
                    match_tank_name = match_tank.strip().lower()
                else:
                    match_tank_name = "unknown"
                # Add all tanks played, including custom
                tank_names.add(match_tank_name)
                pids = [p["id"] for p in match["players"]]
                for p in match["players"]:
                    pid = p["id"]
                    if pid not in stats_by_tank["all"]:
                        stats_by_tank["all"][pid] = {"name": p.get("name", str(pid)), "wins": 0, "losses": 0, "elo": elo_data.get(str(pid), 1000)}
                    if match_tank_name not in stats_by_tank:
                        stats_by_tank[match_tank_name] = {}
                    if pid not in stats_by_tank[match_tank_name]:
                        stats_by_tank[match_tank_name][pid] = {"name": p.get("name", str(pid)), "wins": 0, "losses": 0, "elo": elo_data.get(str(pid), 1000)}
                winner = match.get("winner")
                if winner is not None and winner in pids:
                    stats_by_tank["all"][winner]["wins"] += 1
                    stats_by_tank[match_tank_name][winner]["wins"] += 1
                    loser = [pid for pid in pids if pid != winner]
                    if loser:
                        stats_by_tank["all"][loser[0]]["losses"] += 1
                        stats_by_tank[match_tank_name][loser[0]]["losses"] += 1
    # Always show known tanks, plus all custom tanks played
    tank_names = sorted(list(tank_names))
    for t in known_tanks:
        if t not in tank_names:
            tank_names.append(t)
    def make_pages(tank):
        from constants import TANK_EMOJIS
        stats = stats_by_tank.get(tank, {})
        sorted_stats = sorted(stats.items(), key=lambda x: x[1]["elo"], reverse=True)
        pages = []
        per_page = 10
        # Usa el nombre capitalizado para mostrar y buscar el emoji
        tank_display = tank if tank == "all" else tank.title().replace(" ", "") if tank != "spawner" else "Spawner"
        tank_name_map = {
            "Sniper": "Sniper",
            "Octotank": "Octo Tank",
            "Overlord": "Overlord",
            "Annihilator": "Annihilator",
            "Fighter": "Fighter",
            "Spawner": "Spawner",
            "Other": "Other",
            "All": "all"
        }
        tank_key = tank_name_map.get(tank_display, tank_display)
        # Get emoji as string for embed
        emoji_str = ""
        if tank_key == "Other":
            emoji_str = "❓"
        else:
            emoji_raw = TANK_EMOJIS.get(tank_key, "")
            if emoji_raw:
                emoji_str = emoji_raw
        tank_title = tank_key if tank_key != "all" else "All"
        # Tank config data
        tank_configs = {
            "fighter": {"build": "2/2/2/8/6/8/9/5/0/0", "map": "56x56 – horizontal"},
            "octo tank": {"build": "2/2/2/8/6/8/9/5/0/0", "map": "20x20 - horizontal on edge"},
            "overlord": {"build": "2/2/9/8/6/8/0/7/0/0", "map": "56x56 - vertical"},
            "spawner": {"build": "2/2/5/8/5/8/6/6/0/0", "map": "56x56 - horizontal"},
            "sniper": {"build": "0/0/7/8/5/8/5/9/0/0", "map": "20x20 - horizontal on edge"},
            "annihilator": {"build": "0/0/9/9/6/9/3/6/0/0", "map": "32x32 - vertical"}
        }
        config_text = ""
        config_key = tank.lower()
        if config_key in tank_configs:
            cfg = tank_configs[config_key]
            config_text = f"**Build:** `{cfg['build']}`\n**Map:** {cfg['map']}"
        for i in range(0, len(sorted_stats), per_page):
            embed = discord.Embed(
                title=f"1v1 Leaderboard {emoji_str}{' - ' + tank_title if tank_title != 'All' else ''}",
                color=0xFFD700 if tank_title == "All" else 0x00bfff,
                description=config_text
            )
            for rank, (pid, data) in enumerate(sorted_stats[i:i+per_page], start=i+1):
                embed.add_field(
                    name=f"🏅 #{rank} {data['name']}",
                    value=f"⭐ ELO: **{data['elo']}**\n🏆 Wins: **{data['wins']}** | ❌ Losses: **{data['losses']}**",
                    inline=False
                )
            embed.set_footer(text=f"Page {i//per_page+1}/{(len(sorted_stats)-1)//per_page+1} | Category: {emoji_str} {tank_title}")
            pages.append(embed)
        # Only show config if available (remove 'No config available' message)
        return pages if pages else [discord.Embed(title="1v1 Leaderboard", description="No data found for this category.", color=0xFFD700)]
    pages_by_tank = {tank: make_pages(tank) for tank in ["all"] + tank_names}
    return pages_by_tank, tank_names

def get_leaderboard_channel_config(guild):
    config_path = os.path.join("guild_configs", f"{guild.id}.json")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        return config.get("leaderboard_channel_id"), config.get("leaderboard_message_id"), config_path, config
    return None, None, config_path, {}

def update_leaderboard_message(guild):
    leaderboard_channel_id, leaderboard_message_id, config_path, config = get_leaderboard_channel_config(guild)
    if not leaderboard_channel_id:
        return
    channel = guild.get_channel(leaderboard_channel_id)
    elo_data = load_elo()
    history_file = "match_history.json"
    pages_by_tank, tank_names = make_leaderboard_pages(history_file, elo_data)
    view = LeaderboardTankView(pages_by_tank, tank_names)
    embed = pages_by_tank["all"][0]
    async def send_or_edit():
        msg = None
        if leaderboard_message_id:
            try:
                msg = await channel.fetch_message(leaderboard_message_id)
                await msg.edit(embed=embed, view=view)
            except Exception:
                msg = await channel.send(embed=embed, view=view)
                config["leaderboard_message_id"] = msg.id
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(config, f, indent=2)
        else:
            msg = await channel.send(embed=embed, view=view)
            config["leaderboard_message_id"] = msg.id
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
    return send_or_edit
