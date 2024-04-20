from enum import Enum
import discord
import subprocess
from discord.ext import commands
from discord.commands import Option
from discord import default_permissions

session_name = "Minecraft"

class MinecraftConsole(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
    
    @commands.slash_command(description="Execute command on minecraft server")
    @commands.is_owner()
    @default_permissions(administrator=True)
    async def minecraft_exec(self, ctx, command: Option(str,required = True)):
        if tmux_session_exists(session_name):
            # print(f"The tmux session '{session_name}' exists.")
            wasExecuted, output = await exec_command(command)
            if wasExecuted:
                await ctx.respond(f'Command "{command}" has been executed. \n {output}')
            else:
                await ctx.respond(f'Command "{command}" could not be executed. \n {output}')
        else:
            print(f"The tmux session '{session_name}' does not exist.")
            await ctx.respond(f"The tmux session '{session_name}' does not exist.")
        
        
        

def setup(bot) -> None:
    bot.add_cog(MinecraftConsole(bot))

async def exec_command(command : str):
    # Example command: tmux send-keys -t <session_name> <command> C-m
    tmux_cmd = f"tmux send-keys -t {session_name} '{command}' C-m"
    try:
        result = subprocess.run(tmux_cmd, shell=True, check=True, capture_output=True)
        return True, result.stdout.decode('utf-8')
    except subprocess.CalledProcessError as e:
        return False, e.stderr.decode('utf-8')
    
def tmux_session_exists(session_name):
    try:
        subprocess.run(f"tmux has-session -t {session_name}", shell=True, check=True)
        return True
    except subprocess.CalledProcessError:
        return False