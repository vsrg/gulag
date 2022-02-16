import discord
from discord.ext import commands

from datetime import datetime

from discordbot.utils.constants import colors

from app.objects.player import Player
import app.state.sessions

async def restrict_log(a, t, reason:str):
    """Generate restriction message and send it to hall of shame"""
    if type(t) != Player:
        t: Player = await app.state.sessions.players.from_cache_or_sql(name=t)
    if type(a) != Player:
        a: Player = await app.state.sessions.players.from_cache_or_sql(name=a)

    now = datetime.utcnow()
    embed = discord.Embed(
        timestamp=now
    )

    embed.set_author(
        name=f"{t.name} has been restricted!",
        url=f"https://seventwentyseven.xyz/u/{t.id}"
    )
    embed.add_field(
        name="Admin",
        value=f"[{a.name}](https://seventwentyseven.xyz/u/{a.id})",
        inline=True
    )

    embed.add_field(
        name="Reason",
        value=reason,
        inline=True
    )

    embed.set_footer(
        text="Shame...",
        icon_url="https://seventwentyseven.xyz/static/favicon/favicon-32x32.png"
    )

    embed.set_thumbnail(url=t.avatar_url)

    return embed