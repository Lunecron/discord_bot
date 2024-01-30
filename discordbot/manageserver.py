import os
from enum import Enum

class Server(Enum):
    PAL_SERVER = 'Palserver'
    MINECRAFT_SERVER = 'MinecraftServer'

def start_server(name: Server) -> None:
    if name == Server.PAL_SERVER:
        os.system("sh palworld_start.sh")
    elif name == Server.MINECRAFT_SERVER:
        print("No Mincraft Server yet")
        #os.system("sh mc_start.sh")
    else:
        print(f"No Server found with {name}")
        
def stop_server(name: Server) -> None:
    if name == Server.PAL_SERVER:
        os.system("sh palworld_stop.sh")
    elif name == Server.MINECRAFT_SERVER:
        print("No Mincraft Server yet")
        #os.system("sh mc_stop.sh")
    else:
        print(f"No Server found with {name}")