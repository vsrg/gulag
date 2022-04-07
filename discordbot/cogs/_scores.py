# Normal imports
import app.state
import cmyui
import discord
import discordbot.botconfig as configb
from app.constants.mods import SPEED_CHANGING_MODS
from app.constants.privileges import Privileges
from app.objects.player import Player
from discord.ext import commands
from discord.utils import get
from discord_slash import SlashContext, cog_ext
from discord_slash.utils.manage_commands import create_choice, create_option
from discordbot.utils import constants as dconst
from discordbot.utils import embed_utils as embutils
from discordbot.utils import slashcmd_options as sopt
from discordbot.utils import utils as dutils

# Logging stuff
from cmyui.logging import log
from cmyui.logging import Ansi

class dzifors(commands.Cog):

    # Cog init
    def __init__(self, client):
        self.client = client

    @cog_ext.cog_slash(name = "scores", description = "scores", options = sopt.scores)
    async def _scores(self, ctx: SlashContext, user:str=None, type:str=None, mode:str=None, mods:str="ignore", limit:str=None):
        if not user:
            self_executed = True
        else:
            self_executed = False
        
        # Get user from database
        user = await dutils.getUser(ctx, "id, name, preferred_mode", user)

        #! Return if error occured
        if 'error' in user:
            cmyui.log(f"DISCORD BOT: {ctx.author} tried using /scores but got an error: {user['error']}", Ansi.RED)
            # return await ctx.send(embed = await embutils.emb_gen("no_scores_self"))

            

        return await ctx.send(
            embed = discord.Embed(
                title="This Worked",
                description=f"user: {user}", 
                color=ctx.author.color
            )
        )


# Adding Cog
def setup(client):
    client.add_cog(dzifors(client))