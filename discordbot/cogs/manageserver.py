import os
from enum import Enum
import discord
import asyncio
import subprocess
from discord.ext import commands
from discord.commands import Option

#ServerList includes SERVER_NAME, START_SERVER: name of file to start the server, STOP_SERVER: name of file to stop the server
class ServerList(Enum):
    SERVER_NAME = ['Palworld','Minecraft']
    START_SERVER = ['palworld_start.sh','minecraft_start.sh']
    STOP_SERVER = ['palworld_stop.sh','minecraft_stop.sh']

class Server(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
    
    @commands.slash_command(description="Start a running Server")
    @discord.default_permissions(administrator=True)
    async def startserver(self, ctx, server: Option(str,choices=ServerList.SERVER_NAME.value,required = True)):
        result_message = await start_server(server)
        await ctx.send(result_message)

    @discord.default_permissions(administrator=True)
    @commands.slash_command(description="Stop a running server")
    async def stopserver(self, ctx, server: Option(str,choices=ServerList.SERVER_NAME.value,required = True)):
        result_message = await stop_server(server)
        await ctx.send(result_message)
        
    @discord.default_permissions(administrator=True)
    @commands.slash_command(description="Check Server Status")
    async def server_status(self,ctx):
        await ctx.defer();
        response = await check_tmux_servers()
        await ctx.followup.send(response);
        

def setup(bot) -> None:
    bot.add_cog(Server(bot))

        
async def start_server(name : ServerList.SERVER_NAME.value) -> str:
    if name in ServerList.SERVER_NAME.value:
        index = ServerList.SERVER_NAME.value.index(name)
        startfile = ServerList.START_SERVER.value[index]
        if startfile == '':
                print (f"No startfile with the name '{startfile}' found.")
                return f"No startfile defined."
        else:
            try:
                # Run the shell command asynchronously
                process = await asyncio.create_subprocess_exec("sh", str(startfile), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = await process.communicate()

                # Check if the command was successful
                if process.returncode == 0:
                    print (f"Server '{name}' started successfully!")
                    return f"Server '{name}' started successfully!"
                else:
                    print (f"Error stopping server '{name}': {stderr.decode('utf-8')}")
                    return f"Error stopping server '{name}': {stderr.decode('utf-8')}"
            except Exception as e:
                print (f"An error occurred: {str(e)}")
                return f"An error occurred: {str(e)}"
    else:
        print(f"No Server found with {name}")
        return f"No Server found with {name}"
                
async def stop_server(name : ServerList.SERVER_NAME.value) -> str:
    index = ServerList.SERVER_NAME.value.index(name)
    stopfile = ServerList.STOP_SERVER.value[index]
    if stopfile == '':
            print (f"No stopfile with the name '{stopfile}' found.")
            return f"No stopfile defined."
    else:
        try:
            # Run the shell command asynchronously
            process = await asyncio.create_subprocess_exec("sh", str(stopfile), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = await process.communicate()

            # Check if the command was successful
            if process.returncode == 0:
                print (f"Server '{name}' stopped successfully!")
                return f"Server '{name}' stopped successfully!"
            else:
                print (f"Error stopping server '{name}': {stderr.decode('utf-8')}")
                return f"Error stopping server '{name}': {stderr.decode('utf-8')}"
        except Exception as e:
            print (f"An error occurred: {str(e)}")
            return f"An error occurred: {str(e)}"
            
            
async def check_tmux_servers() -> str:

    tmux_instances = await run_tmux_command()

    # Build the response string
    response = ""
    for server_name in ServerList.SERVER_NAME.value:
        if server_name in tmux_instances:
            response += f"{server_name} = online\n"
        else:
            response += f"{server_name} = offline\n"

    return response
    
async def run_tmux_command():
        try:
            # Get a list of all tmux sessions
            tmux_list_output = subprocess.check_output(["tmux", "list-sessions"], text=True)
            return [line.split(":")[0] for line in tmux_list_output.splitlines()]
        except subprocess.CalledProcessError as e:
            print(f"Error running tmux command: {e}")
            return []