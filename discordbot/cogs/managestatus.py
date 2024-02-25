import os
import discord
import json
from discord.ext import commands
from discord.commands import Option
from discord import default_permissions

##Custom status requires lates pycord build (31.01.2024)
##Install dev branch with:
##pip install git+https://github.com/Pycord-Development/pycord


bot_main_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
config_directory = os.path.join(bot_main_directory, 'config')
config_file_path = os.path.join(config_directory, 'bot_config.json')

class Status(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
        createConfigDir()
        loadconfig(self)
        

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        await set_initial_presence(self)
    
    #Set the activity of the bot
    @commands.slash_command(description="Change Activity")
    @default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def setactivity(self, ctx, type: Option(str, choices=["clear","game","streaming","listening","watching","custom","competing"],required = True), name: Option(str,required = False,default = '') , url: Option(str,required = False, default = '')) -> None:
        await update_status_and_activity(self, self.config.get('status','online'),type,name,url)

        await ctx.respond(f"Aktivität wurde geändert.")
    
    #Set the status of the bot
    @commands.slash_command(description="Change bot status")
    @default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def setstatus(self, ctx, type: Option(str, choices=["online","idle","dnd"],required = True)) ->None:
        await update_status_and_activity(self,type, self.config.get('activity', None) , self.config.get('name', ''), self.config.get('url', ''))
        await ctx.respond(f"Status wurde geändert.")
        

# Create the config directory if it doesn't exist
def createConfigDir():
    os.makedirs(config_directory, exist_ok=True)

def loadconfig(self):

    # Load configuration or create with default values
    if os.path.exists(config_file_path):
        with open(config_file_path, 'r') as file:
            self.config = json.load(file)
    else:
        self.config = {'status': 'online', 'activity': None , 'name': '' , 'url': ''}
        with open(config_file_path, 'w') as file:
            json.dump(self.config, file)

def saveconfig(self):
    with open(config_file_path, 'r') as file:
            old_config = json.load(file)
    #Check if difference between current config and old_config. True: overwrite old_config file
    if old_config['status'] != self.config['status'] or old_config['activity'] != self.config['activity'] or old_config['name'] != self.config['name'] or old_config['url'] != self.config['url']:
        with open(config_file_path, 'w') as file:
            json.dump(self.config, file)

async def set_initial_presence(self):
        # Set the initial status and activity
        initial_status = self.config.get('status', 'online')
        initial_activity_type = self.config.get('activity', None)
        initial_activity_name = self.config.get('name', '')
        initial_activity_url = self.config.get('url', '')
        await update_status_and_activity(self,initial_status,initial_activity_type,initial_activity_name,initial_activity_url)


async def update_status_and_activity(self,status_type:str,activity_type:str,name:str,url:str):
    if status_type == "online":
        status = discord.Status.online
    elif status_type == "idle":
        status = discord.Status.idle
    elif status_type == "dnd":
        status = discord.Status.dnd
    else:
        print("Error: Could not find corresponding status! Taking default: online")
        status = discord.Status.online
        return
    
    if activity_type == "clear":
        print("Activities cleared.")
        act = None
    elif activity_type == "game":
        act = discord.Game(name=name)
    elif activity_type == "streaming":
        if url != '' and ( url.startswith("https://www.twitch.tv/") or url.startswith("https://www.youtube.com/") ):
            act = discord.Streaming(name = name, url = url)
        else:
            act = discord.Streaming(name = name)
            print(f"Stream konnte nicht gefunden werden. Füge eine URL hinzu die wie folgt anfängt: ```https://www.twitch.tv/``` oder ```https://www.youtube.com/```")  
    elif activity_type == "listening":
        act = discord.Activity(type=discord.ActivityType.listening, name=name)
    elif activity_type == "watching":
        act = discord.Activity(type=discord.ActivityType.watching, name=name)
    #Custom status only works in lates dev build (31.01.2024) (see information in the beginning of the doc)
    elif activity_type == "custom":
        act = discord.CustomActivity(name)
    elif activity_type == "competing":
        act = discord.Activity(name=name, type=5)
    else:
        print("Activitiy not found. No activity taken.")
        act = None
    self.config = {'status': status_type ,'activity':activity_type,'name':name,'url':url}
    await self.bot.change_presence(status=status, activity=act)
    saveconfig(self)



def setup(bot):
    bot.add_cog(Status(bot))