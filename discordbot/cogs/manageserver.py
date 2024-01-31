import os
from enum import Enum
import discord
from discord.ext import commands
from discord.commands import Option

class ServerList(Enum):
    PAL_SERVER = 'Palserver'
    MINECRAFT_SERVER = 'MinecraftServer'


class Server(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
    
    @commands.slash_command(description="Start a running Server")
    async def startserver(self, ctx, server: ServerList):
        start_server(server)
        await ctx.respond(f"{server} wurde gestartet!")
        
    @commands.slash_command(description="Stop a running server")
    async def stopserver(self, ctx, server: ServerList):
        stop_server(server)
        await ctx.respond(f"{server} wurde gestopt!")
                
def setup(bot) -> None:
    bot.add_cog(Server(bot))


def start_server(name: ServerList) -> None:
    if name == ServerList.PAL_SERVER:
        os.system("sh palworld_start.sh")
    elif name == ServerList.MINECRAFT_SERVER:
        print("No Mincraft Server yet")
        #os.system("sh mc_start.sh")
    else:
        print(f"No Server found with {name}")
        
def stop_server(name: ServerList) -> None:
    if name == ServerList.PAL_SERVER:
        os.system("sh palworld_stop.sh")
    elif name == ServerList.MINECRAFT_SERVER:
        print("No Mincraft Server yet")
        #os.system("sh mc_stop.sh")
    else:
        print(f"No Server found with {name}")