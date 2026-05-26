#!/usr/bin/env python3
"""
VirusBot — Discord бот с вирусной экономикой.
Команды работают без префикса (!) и с префиксом.
"""

import discord
from discord.ext import commands, tasks
from discord import app_commands
import random
import time as time_module
from typing import Optional
import json
import os
import re

# ========================= НАСТРОЙКИ =========================

MAX_CHARGES = 3
RECHARGE_MINUTES = 30
RECHARGE_SECONDS = RECHARGE_MINUTES * 60
SAVE_FILE = "virus_data.json"
# ==============================================================

PREFIXES = [
    "Смертоносный", "Ядовитый", "Гнилой", "Безумный", "Скрытный",
    "Яростный", "Тлетворный", "Жгучий", "Ледяной", "Призрачный",
    "Мутагенный", "Хаотичный", "Древний", "Безмолвный", "Алчный",
    "Коварный", "Слепой", "Голодный", "Пульсирующий", "Неумолимый"
]

ROOTS = [
    "Ойкококк", "Ойкоштамм", "Ойкоид", "Ойкоплазмоид",
    "Ойкофлю", "Ойкоморф", "Ойкобацилла", "Ойковирион",
    "Ойкоспора", "Ойкотоксин", "Ойкофаг", "Ойконексус",
    "Ойкоспектр", "Ойкокристалл", "Ойкожгут", "Ойкоклин",
    "Ойкоскверн", "Ойкокс", "Ойкозис", "Ойкомицет"
]


class VirusCharges:
    def __init__(self, charges: int = MAX_CHARGES, last_recharge: float = 0.0):
        self.charges = charges
        self.last_recharge = last_recharge if last_recharge else time_module.time()
    
    def use(self) -> bool:
        self._recharge()
        if self.charges > 0:
            self.charges -= 1
            if self.charges < MAX_CHARGES:
                self.last_recharge = time_module.time()
            return True
        return False
    
    def _recharge(self):
        now = time_module.time()
        elapsed = now - self.last_recharge
        recharges = int(elapsed // RECHARGE_SECONDS)
        if recharges > 0:
            self.charges = min(MAX_CHARGES, self.charges + recharges)
            self.last_recharge += recharges * RECHARGE_SECONDS
    
    def time_until_next(self) -> int:
        self._recharge()
        if self.charges >= MAX_CHARGES:
            return 0
        now = time_module.time()
        elapsed = now - self.last_recharge
        return max(0, RECHARGE_SECONDS - int(elapsed % RECHARGE_SECONDS))
    
    def display(self) -> str:
        self._recharge()
        filled = "✴️ " * self.charges
        empty = "░ " * (MAX_CHARGES - self.charges)
        mins = self.time_until_next() // 60
        secs = self.time_until_next() % 60
        if self.charges >= MAX_CHARGES:
            return f"[ {filled}] — заряжено!"
        elif mins > 0:
            return f"[ {filled}{empty}] — след. через {mins} мин."
        else:
            return f"[ {filled}{empty}] — след. через {secs} сек."
    
    def to_dict(self) -> dict:
        return {'charges': self.charges, 'last_recharge': self.last_recharge}
    
    @classmethod
    def from_dict(cls, data: dict) -> 'VirusCharges':
        return cls(data.get('charges', MAX_CHARGES), data.get('last_recharge', 0.0))


class VirusRegistry:
    def __init__(self):
        self._owners = {}
        self._names = {}
    
    def register(self, user_id: str, name: str) -> tuple[bool, str]:
        name = name.strip()
        if not name or len(name) < 3:
            return False, "❌ Название должно быть минимум 3 символа."
        if len(name) > 40:
            return False, "❌ Название не должно превышать 40 символов."
        if name in self._names and self._names[name] != user_id:
            suggestions = self._suggest_similar(name)
            return False, f"❌ Вирус «{name}» уже существует!\n💡 Попробуй: {suggestions}"
        if user_id in self._owners:
            old_name = self._owners[user_id]
            if old_name in self._names:
                del self._names[old_name]
        self._owners[user_id] = name
        self._names[name] = user_id
        return True, f"🦠 Ваш вирус теперь называется «**{name}**»!"
    
    def get_virus(self, user_id: str) -> Optional[str]:
        return self._owners.get(user_id)
    
    def generate_random(self) -> str:
        for _ in range(500):
            name = f"{random.choice(PREFIXES)} {random.choice(ROOTS)}"
            if name not in self._names:
                return name
        base = f"{random.choice(PREFIXES)} {random.choice(ROOTS)}"
        counter = 2
        while f"{base} #{counter}" in self._names:
            counter += 1
        return f"{base} #{counter}"
    
    def _suggest_similar(self, name: str) -> str:
        suggestions = []
        for _ in range(3):
            suggestion = f"{random.choice(PREFIXES)} {random.choice(ROOTS)}"
            if suggestion not in self._names:
                suggestions.append(f"«{suggestion}»")
        if not suggestions:
            suggestions = [f"«{name} №{random.randint(2, 99)}»"]
        return " или ".join(suggestions)


class Player:
    def __init__(self, user_id: str, username: str, registry: VirusRegistry):
        self.user_id = user_id
        self.username = username
        self.registry = registry
        self.balance = 0
        self.strength = 1
        self.time_level = 1
        self.immunity = 1
        self.charges = VirusCharges()
        self.virus_name = registry.generate_random()
        registry.register(user_id, self.virus_name)
        self.infected_by = None
        self.infection_end = 0.0
        self.total_infections = 0
        self.total_income = 0
    
    def rename_virus(self, new_name: str) -> str:
        success, message = self.registry.register(self.user_id, new_name)
        if success:
            self.virus_name = new_name
        return message
    
    def get_duration(self) -> int:
        return 4 + self.time_level
    
    def get_immunity_reduction(self) -> float:
        return self.immunity * 0.15
    
    def infect(self, target: 'Player') -> tuple[bool, str]:
        if not self.charges.use():
            mins = self.charges.time_until_next() // 60
            secs = self.charges.time_until_next() % 60
            return False, f"❌ Нет зарядов! Следующий через {mins} мин {secs} сек."
        if target.user_id == self.user_id:
            return False, "❌ Нельзя заразить самого себя!"
        if target.is_infected():
            remaining = target.get_remaining_time()
            return False, f"❌ {target.username} уже заражён! Осталось {remaining} мин."
        base_duration = self.get_duration()
        reduction = target.get_immunity_reduction()
        duration = max(1, int(base_duration * (1 - reduction)))
        target.infected_by = self.user_id
        target.infection_end = time_module.time() + duration * 60
        income = self.strength * duration
        self.balance += income
        self.total_infections += 1
        self.total_income += income
        return True, (
            f"🦠 **{self.username}** выпустил штамм «**{self.virus_name}**» на **{target.username}**!\n"
            f"⏳ Длительность: **{duration} мин.**\n"
            f"💰 Доход: **{income:,} ✴️**"
        )
    
    def is_infected(self) -> bool:
        return time_module.time() < self.infection_end
    
    def get_remaining_time(self) -> int:
        if not self.is_infected():
            return 0
        return max(1, int((self.infection_end - time_module.time()) / 60) + 1)
    
    def upgrade(self, upgrade_type: str) -> tuple[bool, str]:
        costs = {
            'сила': lambda lvl: int(50 * (lvl ** 1.8) + 30 * lvl),
            'время': lambda lvl: int(40 * (lvl ** 1.7) + 25 * lvl),
            'иммунитет': lambda lvl: int(30 * (lvl ** 1.6) + 20 * lvl),
            's': lambda lvl: int(50 * (lvl ** 1.8) + 30 * lvl),
            't': lambda lvl: int(40 * (lvl ** 1.7) + 25 * lvl),
            'i': lambda lvl: int(30 * (lvl ** 1.6) + 20 * lvl),
        }
        names = {
            'сила': ('🧪 Сила', 'strength'),
            'время': ('⏳ Время', 'time_level'),
            'иммунитет': ('🛡️ Иммунитет', 'immunity'),
            's': ('🧪 Сила', 'strength'),
            't': ('⏳ Время', 'time_level'),
            'i': ('🛡️ Иммунитет', 'immunity'),
        }
        key = upgrade_type.lower()
        if key not in costs:
            return False, "❌ Неизвестный тип. Доступно: `сила(s)`, `время(t)`, `иммунитет(i)`"
        name, attr = names[key]
        current_level = getattr(self, attr)
        cost = costs[key](current_level)
        if self.balance < cost:
            return False, f"❌ Недостаточно ✴️! Нужно **{cost:,}**, у вас **{self.balance:,}**."
        self.balance -= cost
        setattr(self, attr, current_level + 1)
        bonus = ""
        if key in ('время', 't'):
            bonus = f"\n⏳ Длительность: **{self.get_duration()} мин.**"
        elif key in ('сила', 's'):
            bonus = f"\n💰 Доход: **{self.strength} ✴️/мин.**"
        elif key in ('иммунитет', 'i'):
            bonus = f"\n🛡️ Срезает: **{self.get_immunity_reduction()*100:.0f}%** чужого времени"
        return True, f"✅ {name} повышен до уровня **{current_level + 1}**!{bonus}\n💸 Потрачено: **{cost:,} ✴️**"
    
    def profile_embed(self, discord_user) -> discord.Embed:
        base_time = self.get_duration()
        immunity_pct = self.get_immunity_reduction() * 100
        embed = discord.Embed(title=f"👤 Профиль: {self.username}", color=0x9b59b6)
        embed.add_field(name="✴️ Баланс", value=f"**{self.balance:,}** ✴️", inline=False)
        embed.add_field(name="🔋 Заряды", value=self.charges.display(), inline=False)
        embed.add_field(name="🦠 Вирус", value=f"«**{self.virus_name}**»", inline=False)
        embed.add_field(
            name="📊 Прокачка",
            value=(
                f"🧪 Сила: Ур. **{self.strength}** (Доход: {self.strength} ✴️/мин)\n"
                f"⏳ Время: Ур. **{self.time_level}** (Длительность: {base_time} мин)\n"
                f"🛡️ Иммунитет: Ур. **{self.immunity}** (Срезает {immunity_pct:.0f}%)"
            ),
            inline=False
        )
        embed.add_field(
            name="📈 Статистика",
            value=f"Всего заражений: **{self.total_infections}**\nВсего заработано: **{self.total_income:,}** ✴️",
            inline=False
        )
        embed.set_thumbnail(url=discord_user.display_avatar.url)
        return embed
    
    def to_dict(self) -> dict:
        return {
            'user_id': self.user_id, 'username': self.username,
            'balance': self.balance, 'strength': self.strength,
            'time_level': self.time_level, 'immunity': self.immunity,
            'charges': self.charges.to_dict(), 'virus_name': self.virus_name,
            'infected_by': self.infected_by, 'infection_end': self.infection_end,
            'total_infections': self.total_infections, 'total_income': self.total_income,
        }
    
    @classmethod
    def from_dict(cls, data: dict, registry: VirusRegistry) -> 'Player':
        player = cls.__new__(cls)
        player.user_id = data['user_id']
        player.username = data['username']
        player.registry = registry
        player.balance = data['balance']
        player.strength = data['strength']
        player.time_level = data['time_level']
        player.immunity = data['immunity']
        player.charges = VirusCharges.from_dict(data['charges'])
        player.virus_name = data['virus_name']
        player.infected_by = data['infected_by']
        player.infection_end = data['infection_end']
        player.total_infections = data['total_infections']
        player.total_income = data['total_income']
        return player


class VirusBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)
        self.registry = VirusRegistry()
        self.players = {}
    
    async def setup_hook(self):
        self.load_data()
        self.auto_save.start()
        try:
            synced = await self.tree.sync()
            print(f"📡 Синхронизировано {len(synced)} слэш-команд")
        except Exception as e:
            print(f"❌ Ошибка синхронизации: {e}")
    
    def get_player(self, user_id: int, username: str) -> Player:
        uid = str(user_id)
        if uid not in self.players:
            self.players[uid] = Player(uid, username, self.registry)
        else:
            self.players[uid].username = username
        return self.players[uid]
    
    def load_data(self):
        if os.path.exists(SAVE_FILE):
            with open(SAVE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for uid, pdata in data.get('players', {}).items():
                player = Player.from_dict(pdata, self.registry)
                self.players[uid] = player
                if player.virus_name:
                    self.registry._owners[uid] = player.virus_name
                    self.registry._names[player.virus_name] = uid
    
    def save_data(self):
        data = {'players': {uid: p.to_dict() for uid, p in self.players.items()}}
        with open(SAVE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    @tasks.loop(minutes=5)
    async def auto_save(self):
        self.save_data()


bot = VirusBot()


# ==================== ОБРАБОТКА ОБЫЧНЫХ СООБЩЕНИЙ (БЕЗ ПРЕФИКСА) ====================

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    
    # Сначала пробуем обработать как команду с префиксом
    await bot.process_commands(message)
    
    # Если сообщение уже обработано командой — выходим
    if message.content.startswith("!"):
        return
    
    # Обработка сообщений без префикса
    content = message.content.strip()
    if not content:
        return
    
    # Разбираем сообщение: первое слово — команда, остальное — аргументы
    parts = content.split(maxsplit=1)
    cmd = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""
    
    # Извлекаем упоминания из сообщения
    mentioned = message.mentions
    
    # ===== КОМАНДЫ БЕЗ ПРЕФИКСА =====
    
    if cmd in ["п", "p"]:
        target = mentioned[0] if mentioned else message.author
        player = bot.get_player(target.id, target.display_name)
        embed = player.profile_embed(target)
        await message.channel.send(embed=embed)
        return
    
    if cmd in ["в", "v"]:
        player = bot.get_player(message.author.id, message.author.display_name)
        if not args:
            await message.channel.send(f"🦠 Ваш вирус: «**{player.virus_name}**»\n💡 `в Название` — сменить | `в сгенерировать` — случайное")
        elif args.lower() == "сгенерировать":
            name = bot.registry.generate_random()
            msg = player.rename_virus(name)
            await message.channel.send(msg)
            bot.save_data()
        else:
            msg = player.rename_virus(args)
            await message.channel.send(msg)
            bot.save_data()
        return
    
    if cmd in ["з", "z"]:
        if not mentioned:
            await message.channel.send("❌ Упомяни кого заразить: `з @User`")
            return
        target = mentioned[0]
        if target.bot:
            await message.channel.send("❌ Нельзя заразить бота!")
            return
        player = bot.get_player(message.author.id, message.author.display_name)
        victim = bot.get_player(target.id, target.display_name)
        success, msg = player.infect(victim)
        await message.channel.send(msg)
        if success:
            try:
                await target.send(f"🦠 **{message.author.display_name}** заразил вас вирусом «**{player.virus_name}**»!\n⏳ Вы заражены на **{victim.get_remaining_time()} мин.**")
            except:
                pass
            bot.save_data()
        return
    
    if cmd in ["к", "up"]:
        player = bot.get_player(message.author.id, message.author.display_name)
        if not args:
            await message.channel.send("❌ Укажи: `к сила(s)`, `к время(t)`, `к иммунитет(i)`")
            return
        success, msg = player.upgrade(args)
        await message.channel.send(msg)
        if success:
            bot.save_data()
        return
    
    if cmd in ["с", "s"]:
        target = mentioned[0] if mentioned else message.author
        player = bot.get_player(target.id, target.display_name)
        if player.is_infected():
            await message.channel.send(f"🦠 **{target.display_name}** заражён! Осталось: **{player.get_remaining_time()} мин.**")
        else:
            await message.channel.send(f"✅ **{target.display_name}** здоров!")
        return
    
    if cmd in ["топ", "top"]:
        sorted_players = sorted(bot.players.values(), key=lambda p: p.balance, reverse=True)[:10]
        embed = discord.Embed(title="🏆 Топ игроков", color=0xffd700)
        for i, player in enumerate(sorted_players, 1):
            embed.add_field(
                name=f"{i}. {player.username}",
                value=f"✴️ {player.balance:,} | 🦠 «{player.virus_name}» | Зар.: {player.total_infections}",
                inline=False
            )
        await message.channel.send(embed=embed)
        return
    
    if cmd in ["х", "h"]:
        embed = discord.Embed(title="🦠 Вирусный Бот — Команды", color=0x9b59b6)
        embed.add_field(name="📋 Профиль", value="`п` `п @User`", inline=False)
        embed.add_field(name="🦠 Вирус", value="`в Название` `в сгенерировать`", inline=False)
        embed.add_field(name="⚔️ Заразить", value="`з @User`", inline=False)
        embed.add_field(name="⬆️ Прокачка", value="`к сила` `к время` `к иммунитет`", inline=False)
        embed.add_field(name="🩺 Статус", value="`с` `с @User`", inline=False)
        embed.add_field(name="🏆 Топ", value="`топ`", inline=False)
        embed.add_field(name="❓ Помощь", value="`х`", inline=False)
        embed.set_footer(text=f"🔋 Заряды: {MAX_CHARGES} | Восст.: каждые {RECHARGE_MINUTES} мин. | Префикс НЕ нужен!")
        await message.channel.send(embed=embed)
        return


# ==================== СЛЭШ-КОМАНДЫ ====================

@bot.tree.command(name="профиль", description="Посмотреть профиль игрока")
@app_commands.describe(игрок="Игрок (необязательно)")
async def slash_profile(interaction: discord.Interaction, игрок: discord.Member = None):
    target = игрок or interaction.user
    player = bot.get_player(target.id, target.display_name)
    embed = player.profile_embed(target)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="вирус", description="Показать или сменить название вируса")
@app_commands.describe(название="Новое название (или 'сгенерировать' для случайного)")
async def slash_virus(interaction: discord.Interaction, название: str = None):
    player = bot.get_player(interaction.user.id, interaction.user.display_name)
    if not название:
        await interaction.response.send_message(f"🦠 Ваш вирус: «**{player.virus_name}**»")
        return
    if название.lower() == "сгенерировать":
        название = bot.registry.generate_random()
    message = player.rename_virus(название)
    await interaction.response.send_message(message)
    bot.save_data()


@bot.tree.command(name="заразить", description="Заразить игрока вирусом")
@app_commands.describe(цель="Кого заразить")
async def slash_infect(interaction: discord.Interaction, цель: discord.Member):
    if цель.bot:
        await interaction.response.send_message("❌ Нельзя заразить бота!", ephemeral=True)
        return
    player = bot.get_player(interaction.user.id, interaction.user.display_name)
    victim = bot.get_player(цель.id, цель.display_name)
    success, message = player.infect(victim)
    await interaction.response.send_message(message)
    if success:
        try:
            await цель.send(f"🦠 **{interaction.user.display_name}** заразил вас вирусом «**{player.virus_name}**»!\n⏳ Вы заражены на **{victim.get_remaining_time()} мин.**")
        except:
            pass
        bot.save_data()


@bot.tree.command(name="прокачать", description="Улучшить характеристику вируса")
@app_commands.describe(характеристика="Что качать: сила, время, иммунитет")
async def slash_upgrade(interaction: discord.Interaction, характеристика: str):
    player = bot.get_player(interaction.user.id, interaction.user.display_name)
    success, message = player.upgrade(характеристика)
    await interaction.response.send_message(message)
    if success:
        bot.save_data()


@bot.tree.command(name="статус", description="Проверить статус заражения")
@app_commands.describe(игрок="Игрок (необязательно)")
async def slash_status(interaction: discord.Interaction, игрок: discord.Member = None):
    target = игрок or interaction.user
    player = bot.get_player(target.id, target.display_name)
    if player.is_infected():
        await interaction.response.send_message(f"🦠 **{target.display_name}** заражён! Осталось: **{player.get_remaining_time()} мин.**")
    else:
        await interaction.response.send_message(f"✅ **{target.display_name}** здоров!")


@bot.tree.command(name="топ", description="Топ-10 игроков по балансу")
async def slash_top(interaction: discord.Interaction):
    sorted_players = sorted(bot.players.values(), key=lambda p: p.balance, reverse=True)[:10]
    embed = discord.Embed(title="🏆 Топ игроков", color=0xffd700)
    for i, player in enumerate(sorted_players, 1):
        embed.add_field(
            name=f"{i}. {player.username}",
            value=f"✴️ {player.balance:,} | 🦠 «{player.virus_name}» | Зар.: {player.total_infections}",
            inline=False
        )
    await interaction.response.send_message(embed=embed)


# ==================== ОБЫЧНЫЕ КОМАНДЫ С ПРЕФИКСОМ (для совместимости) ====================

@bot.command(name="п", aliases=["p"])
async def cmd_profile(ctx, member: discord.Member = None):
    target = member or ctx.author
    player = bot.get_player(target.id, target.display_name)
    embed = player.profile_embed(target)
    await ctx.send(embed=embed)


@bot.command(name="в", aliases=["v"])
async def cmd_virus(ctx, *, name: str = None):
    player = bot.get_player(ctx.author.id, ctx.author.display_name)
    if not name:
        await ctx.send(f"🦠 Ваш вирус: «**{player.virus_name}**»\n💡 `в Название` — сменить | `в сгенерировать` — случайное")
        return
    if name.lower() == "сгенерировать":
        name = bot.registry.generate_random()
    message = player.rename_virus(name)
    await ctx.send(message)
    bot.save_data()


@bot.command(name="з", aliases=["z"])
async def cmd_infect(ctx, *, target: discord.Member = None):
    if not target:
        await ctx.send("❌ Укажи цель: `з @User`")
        return
    if target.bot:
        await ctx.send("❌ Нельзя заразить бота!")
        return
    player = bot.get_player(ctx.author.id, ctx.author.display_name)
    victim = bot.get_player(target.id, target.display_name)
    success, message = player.infect(victim)
    await ctx.send(message)
    if success:
        try:
            await target.send(f"🦠 **{ctx.author.display_name}** заразил вас вирусом «**{player.virus_name}**»!\n⏳ Вы заражены на **{victim.get_remaining_time()} мин.**")
        except:
            pass
        bot.save_data()


@bot.command(name="к", aliases=["up"])
async def cmd_upgrade(ctx, *, upgrade_type: str = None):
    if not upgrade_type:
        await ctx.send("❌ Укажи: `к сила(s)`, `к время(t)`, `к иммунитет(i)`")
        return
    player = bot.get_player(ctx.author.id, ctx.author.display_name)
    success, message = player.upgrade(upgrade_type)
    await ctx.send(message)
    if success:
        bot.save_data()


@bot.command(name="с", aliases=["s"])
async def cmd_status(ctx, member: discord.Member = None):
    target = member or ctx.author
    player = bot.get_player(target.id, target.display_name)
    if player.is_infected():
        await ctx.send(f"🦠 **{target.display_name}** заражён! Осталось: **{player.get_remaining_time()} мин.**")
    else:
        await ctx.send(f"✅ **{target.display_name}** здоров!")


@bot.command(name="топ", aliases=["top"])
async def cmd_top(ctx):
    sorted_players = sorted(bot.players.values(), key=lambda p: p.balance, reverse=True)[:10]
    embed = discord.Embed(title="🏆 Топ игроков", color=0xffd700)
    for i, player in enumerate(sorted_players, 1):
        embed.add_field(
            name=f"{i}. {player.username}",
            value=f"✴️ {player.balance:,} | 🦠 «{player.virus_name}» | Зар.: {player.total_infections}",
            inline=False
        )
    await ctx.send(embed=embed)


@bot.command(name="х", aliases=["h"])
async def cmd_help(ctx):
    embed = discord.Embed(title="🦠 Вирусный Бот — Команды", color=0x9b59b6)
    embed.add_field(name="📋 Профиль", value="`п` `п @User`", inline=False)
    embed.add_field(name="🦠 Вирус", value="`в Название` `в сгенерировать`", inline=False)
    embed.add_field(name="⚔️ Заразить", value="`з @User`", inline=False)
    embed.add_field(name="⬆️ Прокачка", value="`к сила` `к время` `к иммунитет`", inline=False)
    embed.add_field(name="🩺 Статус", value="`с` `с @User`", inline=False)
    embed.add_field(name="🏆 Топ", value="`топ`", inline=False)
    embed.add_field(name="❓ Помощь", value="`х`", inline=False)
    embed.set_footer(text=f"🔋 Заряды: {MAX_CHARGES} | Восст.: каждые {RECHARGE_MINUTES} мин. | Префикс НЕ нужен!")
    await ctx.send(embed=embed)


# ==================== ОБРАБОТКА ОШИБОК ====================

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ Игрок не найден. Упомяни его через @")
    elif isinstance(error, commands.CommandNotFound):
        pass
    elif isinstance(error, commands.MissingRequiredArgument):
        pass
    else:
        print(f"❌ Ошибка: {error}")


@bot.event
async def on_ready():
    print(f"🦠 {bot.user} запущен!")
    print(f"📊 Игроков загружено: {len(bot.players)}")
    print(f"💡 Команды без префикса: п в з к с топ х")
    print(f"💡 Слэш-команды: /профиль /вирус /заразить /прокачать /статус /топ")


if __name__ == "__main__":
    bot.run(TOKEN)
