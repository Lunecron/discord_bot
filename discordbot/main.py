from typing import Final
import os
from dotenv import load_dotenv
import discord
from discord import Bot, Message ,Intents
from discord.commands import Option
from responses import get_response
from manageserver import Server,start_server,stop_server
import sys




# Load TOKEN
load_dotenv()
TOKEN: Final[str] = os.getenv('DISCORD_TOKEN')

# Bot Setup
intents:Intents = Intents.default()
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
    
@bot.event
async def on_message(message: Message) -> None:
    #Disable bot reacting on bots/itself
    if message.author.bot:
        return
            
    username: str = str(message.author)
    user_message: str  = message.content
    channel: str  = str(message.channel)
        
    print(f"[{channel}] {username} said:'{user_message}'")
        
    await send_message(message,user_message)
    
#ServerTypes can be found in manageserver
@bot.slash_command(description="Start a running Server")
async def startserver(ctx, server: Server):
    start_server(server)
    await ctx.respond(f"{server} wurde gestartet!")
    
@bot.slash_command(description="Stop a running server")
async def stopserver(ctx, server: Server):
    stop_server(server)
    await ctx.respond(f"{server} wurde gestopt!")

@bot.slash_command(description="Stop the bot")
async def killbot(ctx):
    await ctx.respond(f"Bot wurde beendet!")
    sys.exit()

    
def main() -> None:
    bot.run(token=TOKEN)

if __name__ == '__main__':
    main()