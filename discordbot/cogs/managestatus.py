import os
import discord
from discord.ext import commands
from discord.commands import Option

##Custom status requires lates pycord build (31.01.2024)
##Install dev branch with:
##pip install git+https://github.com/Pycord-Development/pycord

class Status(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
    
    #Set the activity of the bot
    @commands.slash_command(description="Change Activity")
    @discord.default_permissions(administrator=True)
    @discord.has_permissions(administrator=True)
    async def setactivity(self, ctx, type: Option(str, choices=["clear","game","streaming","listening","watching","custom","competing"],required = True), name: Option(str,required = False,default = '') , url: Option(str,required = False, default = '')) -> None:
        if type == "clear":
            act = discord.Game(name='')
            await self.bot.change_presence(activity=act)
            await ctx.respond(f"Aktivität wurde gelöscht!")
            return
        elif name == '':
            await ctx.respond(f"Die Aktivität benötigt einen Namen.")
            return
        elif type == "game":
            act = discord.Game(name=name)
        elif type == "streaming":
            if url != '' and ( url.startswith("https://www.twitch.tv/") or url.startswith("https://www.youtube.com/") ):
                act = discord.Streaming(name = name, url = url)
            else:
                await ctx.respond(f"Stream konnte nicht gefunden werden. Füge eine URL hinzu die wie folgt anfängt: ```https://www.twitch.tv/``` oder ```https://www.youtube.com/```")
                
        elif type == "listening":
            act = discord.Activity(type=discord.ActivityType.listening, name=name)
        elif type == "watching":
            act = discord.Activity(type=discord.ActivityType.watching, name=name)
        #Custom status only works in lates dev build (31.01.2024) (see information in the beginning of the doc)
        elif type == "custom":
            act = discord.CustomActivity(name)
        elif type == "competing":
            act = discord.Activity(name=name, type=5)
        else:
            print("Activitiy not found")
            await ctx.respond(f"Aktivität-Typ {type} wurde nicht gefunden!")
            
        await self.bot.change_presence(activity=act)
        await ctx.respond(f"Aktivität wurde geändert.")
    
    #Set the status of the bot
    @commands.slash_command(description="Change bot status")
    @discord.default_permissions(administrator=True)
    @discord.has_permissions(administrator=True)
    async def setstatus(self, ctx, type: Option(str, choices=["online","idle","dnd"],required = True)) ->None:
        if type == "online":
            status = discord.Status.online
        elif type == "idle":
            status = discord.Status.idle
        elif type == "dnd":
            status = discord.Status.dnd
        else:
            await ctx.respond(f"Status konnte nicht geändert werden. {type} ist kein gültiger Status.")
            return
        await self.bot.change_presence(status = status)
        await ctx.respond(f"Status wurde geändert.")
        

#Saves last status into local file
def saveStatus() -> None:
    print("#1 Not Implemented")
#Saves last activity into local file
def saveActivity() -> None:
    print("#2 Not Implemented")


def setup(bot):
    bot.add_cog(Status(bot))