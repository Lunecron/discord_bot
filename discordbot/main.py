from typing import Final
import os
import sys
from dotenv import load_dotenv
import discord
import discord.commands
from discord import Bot, Message ,Intents
from discord.commands import Option
from discord.ext import commands
from responses import get_response



#Necessary:
#dotenv:#
## pip install python-dotenv ##
#pycord (with support of new features like slash_command,etc):#
## pip install git+https://github.com/Pycord-Development/pycord ##

# Load TOKEN
load_dotenv()
TOKEN: Final[str] = os.getenv('DISCORD_TOKEN') # type: ignore

# Bot Setup
intents:Intents = Intents.default()
intents.presences = True
intents.members = True
intents.message_content = True
bot: Bot = Bot(intents=intents)



#Message functionality
async def send_message(message: Message, user_message:str) -> None:
    if not user_message:
        print('(Message was empty because intents were not enabled probably)')
        return
    is_private : bool = user_message[0]== '?'
    if is_private:
        user_message = user_message[1:]  

    try:
        response:str = get_response(user_message)
        print(f"[{message.channel}] {bot.user} said: {response}")
        await message.author.send(response) if is_private else await message.channel.send(response)
    except Exception as e:
        print(e)
        
 
 
#Statup Bot
@bot.event
async def on_ready() -> None:
    print(f'{bot.user} is now running!')


    
# @bot.event
# async def on_message(message: Message) -> None:
    # #Disable bot reacting on bots/itself
    # if message.author.bot:
        # return
            
    # username: str = str(message.author)
    # user_message: str  = message.content
    # channel: str  = str(message.channel)
        
    # print(f"[{channel}] {username} said:'{user_message}'")
        
    # await send_message(message,user_message)
    
#Slash commands are seperated in responding cogs
#Include Cogs
script_path = os.path.abspath(__file__)
script_directory = os.path.dirname(script_path)
for filename in os.listdir(script_directory + "/cogs"):
    if filename.endswith(".py"):
        bot.load_extension(f"cogs.{filename[:-3]}")


#Command to kill the bot if necessary
@bot.slash_command(description="Stop the bot")
@commands.is_owner()
async def killbot(ctx):
    await ctx.respond(f"Bot wurde beendet!")
    sys.exit()

    
def main() -> None:
    bot.run(token=TOKEN)

if __name__ == '__main__':
    main()