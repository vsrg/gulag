import discord
from discord.ext import commands

import discordbot.botconfig as configb
from discordbot.utils.constants import colors

import app.state.discordbot as dbot

prefix = configb.PREFIX
embed_list = {
    "permission_view_restrict": {
        "title": "Error",
        "description": f"Due to security reasons, viewing profiles of restricted users is only available in staff channels.",
        "color": colors.red,
        "footer": "default",
        "delete_after": 5
    },
    "not_linked": {
        "title": "Error",
        "description": f"This user donesn't have their discord connected, you can always try with their username on server.",
        "color": colors.red,
        "footer": "default",
        "delete_after": 5
    },
    "not_linked_self": {
        "title": "Error",
        "description": f"You don't have your profile linked, type `{prefix}help link` to find out how to link your profile.",
        "color": colors.red,
        "footer": "default",
        "delete_after": 5
    },
    "usr_not_found": {
        "title": "Error",
        "description": f"Specified user doesn't exist, maybe you made a typo?.",
        "color": colors.red,
        "footer": "default",
        "delete_after": 5
    },
    "restricted_self": {
        "title": "Error",
        "description": f"You can't use this command because you're restricted.",
        "color": colors.red,
        "footer": "default",
        "delete_after": 5
    },
    "module_disabled": {
        "title": "Error",
        "description": f"This module has been disabled by administrator",
        "color": colors.red,
        "footer": "default",
        "delete_after": 5
    },
    "command_disabled": {
        "title": "Error",
        "description": f"This command has been disabled by administrator.",
        "color": colors.red,
        "footer": "default",
        "delete_after": 5
    },
    "cmd_admin_channel": {
        "title": "Error",
        "description": f"For security reasons, this command is available only in admin channels.",
        "color": colors.red,
        "footer": "default",
        "delete_after": 5
    },
    "rx_mania": {
        "title": "Error",
        "description": f"Relax can not be used with mania.",
        "color": colors.red,
        "footer": "default",
        "delete_after": 5
    },
    "ap_no_std": {
        "title": "Error",
        "description": f"Autopilot can be used only with standard.",
        "color": colors.red,
        "footer": "default",
        "delete_after": 5
    },
    "alr_restricted": {
        "title": "Error",
        "description": f"This player is already restricted.",
        "color": colors.red,
        "footer": "default",
        "delete_after": 5
    },
    "not_restricted": {
        "title": "Error",
        "description": f"This player is not restricted.",
        "color": colors.red,
        "footer": "default",
        "delete_after": 5
    },
    "no_perms_admin": {
        "title": "Error",
        "description": f"You must be an admin or higher to use this command.",
        "color": colors.red,
        "footer": "default",
        "delete_after": 5
    },
    "no_perms": {
        "title": "Error",
        "description": f"You don't have permissions to use this command.",
        "color": colors.red,
        "footer": "default",
        "delete_after": 5
    },
    "page_not_num": {
        "title": "Error",
        "description": f"Page must be a __whole__ number.",
        "color": colors.red,
        "footer": "default",
        "delete_after": 5
    },
    "discord_no_osu": {
        "title": "Critical Error",
        "description": f"Your discord is linked but there's no ID entry mtching your id in users table, report that to admins now.",
        "color": colors.red,
        "footer": "default",
        "delete_after": None
    },
    "command_worky": {
        "title": "Task Failed Successfully",
        "description": f"This command works lmfao aint no way",
        "color": colors.green,
        "footer": "default",
        "delete_after": 5
    },
    "scores_over_limit": {
        "title": "Wrong value in index",
        "description": "You entered a number higher than 100 or less than 1. Change index to a number in the range between 1 and 100.",
        "color": colors.red,
        "footer": "default",
        "delete_after": 5
    },
    "not_integer": {
        "title": "Wrong value in index",
        "description": "The thing you entered in index, is not a number. Change index to a number, preferably in the range between 1 and 100.",
        "color": colors.red,
        "footer": "default",
        "delete_after": 5
    },
    "not_enough_scores_self": {
        "title": "You don't have enough scores",
        "description": "You don't have enough scores, but I'll give you a score that is the last I found.",
        "color": colors.red,
        "footer": "default",
        "delete_after": 5
    },
    "no_scores_self": {
        "title": "No scores found",
        "description": f"I failed to find any scores for you. Try setting some, and come back later. If you think this was a mistake, feel free to ping {configb.ROLES['dev']}",
        "color": colors.red,
        "footer": "default",
        "delete_after": 5
    },
}

DEFAULT_FOOTER = f"Version {dbot.botversion} | Bot Creators: def750, grafika dzifors"
client = dbot.client

async def emb_gen(embed_name):
    try:
        emb = embed_list[embed_name]
    except:
        raise IndexError('Embed not found')
    embed = discord.Embed(title=emb['title'], description=emb['description'], color=emb['color'], delete_after=emb["delete_after"])
    if emb['footer'] == "default":
        embed.set_footer(text=DEFAULT_FOOTER)

    if emb["delete_after"] == None:
        return embed
    else:
        delete_after = emb["delete_after"]
        return (embed, delete_after)