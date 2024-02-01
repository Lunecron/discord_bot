import os
from enum import Enum
import discord
from discord.ext import commands
from discord.commands import Option

#ServerList includes SERVER_NAME, START_SERVER: name of file to start the server, STOP_SERVER: name of file to stop the server
class ServerList(Enum):
    SERVER_NAME = ['Palworld','Minecraft']
    START_SERVER = ['palworld_start.sh','']
    STOP_SERVER = ['palworld_stop.sh','']

class Server(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
    
    @commands.slash_command(description="Start a running Server")
    @discord.default_permissions(administrator=True)
    async def startserver(self, ctx, server: Option(str,choices=ServerList.SERVER_NAME.value,required = True)):
        if start_server(server):
            await ctx.respond(f"{server} wurde gestartet!")
        else:
            await ctx.respond(f"{server} konnte nicht gestartet werden!")

    @discord.default_permissions(administrator=True)
    @commands.slash_command(description="Stop a running server")
    async def stopserver(self, ctx, server: Option(str,choices=ServerList.SERVER_NAME.value,required = True)):
        if stop_server(server):
            await ctx.respond(f"{server} wurde gestopt!")
        else:
            await ctx.respond(f"{server} konnte nicht gestopt werden!")    

def setup(bot) -> None:
    bot.add_cog(Server(bot))


def start_server(name : ServerList.SERVER_NAME.value) -> bool:
    if name in ServerList.SERVER_NAME.value:
        index = ServerList.SERVER_NAME.value.index(name)
        startfile = ServerList.START_SERVER.value[index]
        if startfile == '':
            print (f"No startfile with the name '{startfile}' found.")
            return False
        else:
            os.system("sh " + str(startfile))
            print (f"{name} Server started.")
            return True
    else:
        print(f"No Server found with {name}")
        return False
        
def stop_server(name : ServerList.SERVER_NAME.value) -> bool:
    if name in ServerList.SERVER_NAME.value:
        index = ServerList.SERVER_NAME.value.index(name)
        stopfile = ServerList.STOP_SERVER.value[index]
        if stopfile == '':
            print (f"No stopfile with the name '{stopfile}' found.")
            return False
        else:
            os.system("sh " + str(stopfile))
            print (f"{name} Server stoped.")
            return True
    else:
        print(f"No Server found with {name}")
        return False