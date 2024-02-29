import re
import requests
import json
import discord
import os
from discord.ext import commands,tasks
from discord.commands import Option
import json
from bs4 import BeautifulSoup
import time
import asyncio


#To convert html to markdown
import markdownify

#Directory of the main file of the bot
bot_main_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
temp_images_directory = os.path.join(bot_main_directory, 'temp_images')

temp_filename= "temp.jpg"

# Dictionary to store scheduled deletions
scheduled_deletions = {}

#Sorting for mangadex
order = {
    "relevance": "desc",
    "followedCount": "desc",
}
final_order_query = {}
# { "order[rating]": "desc", "order[followedCount]": "desc" }
for key, value in order.items():
    final_order_query[f"order[{key}]"] = value


search_on_mangadex = {"Mangaserie","Light Novel","Mangaserie/Webtoon","Mangaserie/Manhua","Mangaserie/Manhwa","One-Shot","H-Manga"}
search_on_anilist = {"Animeserie","Animeserie/TV","Animeserie/OVA","Animeserie/ONA","Special","Special/OAD","Special/ONA","Special/OVA","Special/TV","Movie","Movie/TV","Movie/ONA","Movie/OVA","Hentai","Hentai/OVA"}
    

class AnimeAndManga(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
        createImageDir()

    # @commands.Cog.listener()
    # async def on_ready(self,ctx):
    #     self.bot.add_view(ButtonView())
    
    @commands.slash_command(description="Search Anime")
    async def search_anime(self, ctx, name: Option(str,required = True, default = '')):
        if not name:
            await ctx.respond("Please enter a name.")
        else:
            await ctx.defer()
            await anilist(ctx, name)

    @commands.slash_command(description="Search Manga")
    async def search_manga(self, ctx, name: Option(str, required = True, default = '')):
        if not name:
            await ctx.respond("Please enter a name.")
        else:
            await ctx.defer()
            await mangadex(ctx, name)

def setup(bot) -> None:
    bot.add_cog(AnimeAndManga(bot))

async def anilist(ctx,name : str):
    #Using Anilist API for Anime
    deletion_time = 60 # Time till message gets deleted
    series_type = "Anime"
    anime_info = search_anime_info(name)

    if anime_info:
        description_markdown = markdownify.markdownify(anime_info['description'])
        
        #Correct formationg of series_type
        if anime_info['format']:
            #Special case of the name One-Shot
            if anime_info['format'].lower() == "one_shot":
                format_correct = "One-Shot"
            else:
                format_correct = anime_info['format'][0].upper() + anime_info['format'][1:].lower()

            series_type += "/"+ format_correct

        if anime_info['english_title'] == None or anime_info['english_title'] == '':
                anime_info['english_title'] = anime_info['romaji_title']
                anime_info['romaji_title'] = None


        embed = discord.Embed(title=anime_info['english_title'], description=description_markdown, color=0x7289da, url=f"https://anilist.co/anime/{anime_info['id']}")
        embed.add_field(name="Typ", value=str(series_type), inline=False)
        if anime_info['romaji_title'] != None or anime_info['romaji_title'] !='':
            embed.add_field(name="Romaji Title", value=anime_info['romaji_title'], inline=False)
        embed.set_thumbnail(url=anime_info['cover_image_url'])
        name_and_search_type = [name,"anime"]
        button_view = ButtonView(ctx,name_and_search_type)
        message = await ctx.followup.send(embed = embed, view=button_view) 
        scheduled_deletions[message.id] = asyncio.create_task(delete_after_delay(ctx,message,deletion_time,button_view))

        # Enable the button after 1 second
        await button_view.enable_after_delay()
    else:
        await ctx.followup.send(f"No information found for '{name}'")

def search_anime_info(title):
    query = '''
    query ($search: String) {
      Media (search: $search, type: ANIME) {
        id
        title {
          romaji
          english
        }
        format
        description
        coverImage {
          extraLarge
        }
      }
    }
    '''

    variables = {
        'search': title,
        'type' : "ANIME"
    }

    url = 'https://graphql.anilist.co'

    response = requests.post(url, json={'query': query, 'variables': variables})
    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        data = response.json()
        anime_info = data["data"]["Media"]

        # Check if any media was found in the response
        if anime_info:
            anime_id = anime_info["id"]
            anime_format = anime_info["format"]
            romaji_title = anime_info['title']['romaji']
            english_title = anime_info['title']['english']
            description = anime_info["description"]
            cover_image_url = anime_info['coverImage']['extraLarge']

            return {
                'id': anime_id,
                'format': anime_format,
                'romaji_title': romaji_title,
                'english_title': english_title,
                'description': description,
                'cover_image_url': cover_image_url,
            }

    # If something went wrong or no matching media found, return None
    return None


async def mangadex(ctx, name):
    #Using mangadex api for Webtoon and Manga
    base_url = "https://api.mangadex.org"
    deletion_time = 60 # Time till message gets deleted
    manga_params = {"title": name, **final_order_query}
    mangadex_response = requests.get(f"{base_url}/manga", params=manga_params)
    has_thumbnail:  bool = False
    
    if mangadex_response.status_code == 200:
        mangadex_data = mangadex_response.json()["data"]
        manga_info = mangadex_data[0] if mangadex_data else None
        if manga_info:
            id = manga_info['id']
            cover_id = [rel['id'] for rel in manga_info['relationships'] if rel.get('type') == 'cover_art'][0]
            series_type = manga_info['type'].capitalize()
            title = manga_info['attributes']['title']['en']

            #Add alternative titles
            alt_title=''
            alt_titles_en = [title["en"] for title in manga_info["attributes"]["altTitles"] if "en" in title]
            alt_titles_ja_ro = [title["ja-ro"] for title in manga_info["attributes"]["altTitles"] if "ja-ro" in title]

            for x in range(len(alt_titles_en)):
                alt_title += alt_titles_en[x] + "\n"
            for y in range(len(alt_titles_ja_ro)):
                alt_title += alt_titles_ja_ro[y] + "\n"

            description = manga_info["attributes"]["description"]["en"]
            #Try finding cover_art over cover_id
            mangadex_response_cover = requests.get(f"{base_url}/cover/{cover_id}")
                
            if mangadex_response_cover.status_code == 200:
                manga_cover_filename = mangadex_response_cover.json()["data"]['attributes']['fileName']
                cover_image_url = f"https://uploads.mangadex.org/covers/{id}/{manga_cover_filename}.512.jpg"
                temp_filename = manga_cover_filename
                temp_filename = change_filename_ending(temp_filename,cover_image_url)
                if download_image(cover_image_url, temp_filename):
                    print("Thumbnail downloaded")
                    has_thumbnail = True
                else:
                    print("Thumbnail could not be downloaded")
                    has_thumbnail = False
                    
            else:
                #Try finding cover_art with include extension of mangadex
                mangadex_response_cover = requests.get(f"{base_url}/manga/{id}?includes[]=cover_art")
                
                if mangadex_response_cover.status_code == 200:
                    mangadex_data = mangadex_response_cover.json()["data"]
                    manga_cover_filename = [rel['attributes']['fileName'] for rel in mangadex_data['relationships'] if rel.get('type') == 'cover_art'][0]
                    cover_image_url = f"https://uploads.mangadex.org/covers/{id}/{manga_cover_filename}.512.jpg"
                    temp_filename = manga_cover_filename
                    temp_filename = change_filename_ending(temp_filename,cover_image_url)
                    if download_image(cover_image_url, temp_filename):
                        print("Thumbnail downloaded")
                        has_thumbnail = True
                    else:
                        print("Thumbnail could not be downloaded")
                        has_thumbnail = False

                else:
                    #No cover found: filler image
                    #no_cover.jpg needs to be in the root folder of the bot
                    temp_filename = 'no_cover.jpg'
                    print("Using filler thumbnail")
            
            if has_thumbnail:
                file_and_dir = os.path.join(temp_images_directory,temp_filename)
                file = discord.File(file_and_dir)  
                embed = discord.Embed(title=title, description=description, color=0xffa500,url=f'https://mangadex.org/manga/{id}')
                embed.add_field(name="Typ", value=str(series_type), inline=False)
                if alt_title != '':
                    embed.add_field(name="Alt Title", value=alt_title, inline=False)
                embed.set_thumbnail(url=f'attachment://{temp_filename}')
                name_and_search_type = [name,"manga"]
                file_entry = {'filename' : temp_filename, 'file_and_dir':file_and_dir}
                button_view = ButtonView(ctx,name_and_search_type,file_entry)
                message = await ctx.followup.send(file=file, embed=embed , view=button_view)
                scheduled_deletions[message.id] = asyncio.create_task(delete_after_delay(ctx,message,deletion_time,button_view))

                file.close()
                # Enable the button after 1 second
                await button_view.enable_after_delay()
            else:
                embed = discord.Embed(title=title, description=description, color=0xffa500,url=f'https://mangadex.org/manga/{id}')
                embed.add_field(name="Typ", value=str(series_type), inline=False)
                embed.add_field(name="Alt Title", value=alt_title, inline=False)
                name_and_search_type = [name,"manga"]
                button_view = ButtonView(ctx,name_and_search_type)
                message = await ctx.followup.send(embed = embed, view=button_view) 
                scheduled_deletions[message.id] = asyncio.create_task(delete_after_delay(ctx,message,deletion_time,button_view))

                # Enable the button after 1 second
                await button_view.enable_after_delay()
            
            
        else:
            await ctx.followup.send(f"No information found for '{name}' on MangaDex", ephemeral= True)
    else:
        await ctx.followup.send("Error accessing MangaDex API", ephemeral= True)

#delete temp image
def delete_temp_file(temp_filename)-> None:
    file_and_dir = os.path.join(temp_images_directory,temp_filename)
    try:
        os.remove(file_and_dir)
        print(f"Temporary file {temp_filename} deleted.")
    except Exception as e:
        print(f"Error deleting temporary file ({temp_filename}): {e}")

#download image for thumbnail
def download_image(url, temp_filename) -> bool:
    file_and_dir = os.path.join(temp_images_directory,temp_filename)
    if os.path.exists(file_and_dir) and os.path.isfile(file_and_dir):
            print(f'The file {file_and_dir} does already exist.')
            return True
    elif os.path.exists(temp_images_directory):
        response = requests.get(url)
        if response.status_code == 200:
                with open(file_and_dir, 'wb') as f:
                    f.write(response.content)
                f.close() # Close the file explicitly
                response.close()  # Close the response explicitly
                return True
        else:
            print(f'The request for "{url}" denied!')
            return False
    else:
        print(f'The path {file_and_dir} does not exist.')
        return False


#download json file for request testing
#just for debugging
def download_file(data):
    with open("data.json", 'w') as json_file:
            json.dump(data, json_file, indent=4)

# Create the temp_images directory if it doesn't exist
def createImageDir():
    os.makedirs(temp_images_directory, exist_ok=True)
        
#check ending of the image in the url and change temp_filename corresponding
def change_filename_ending(temp_filename,url) -> str:
    if url.lower().endswith('.png'):
        temp_filename = temp_filename[:-4]+'.png'
        return temp_filename
    elif url.lower().endswith('.jpg'):
        temp_filename = temp_filename[:-4]+'.jpg'
        return temp_filename
    else:
        print("No correct thumbnail format, trying .jpg:")
        return temp_filename 
    
class ButtonView(discord.ui.View):

    def __init__(self,ctx,name_and_search_type,file_entry = []):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.filename = []
        self.file_path = []
        self.timer_button = self.get_timer_button()
        self.get_filenames_and_files(file_entry)
        self.name = name_and_search_type[0]
        self.search_type = name_and_search_type[1]
        


    async def on_timeout(self):
        if self is not None:
            await self.message.edit(view=None)

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("You are not allowed to interact with this paginator.", ephemeral=True)
            return False
        return True

    async def enable_after_delay(self):
        time.sleep(1)
        # Enable the button
        for child in self.children:
            if isinstance(child, discord.ui.Button) and child.custom_id != "button_timer":
                child.disabled = False
        await self.message.edit(view=self)

    def get_timer_button(self):
        for child in self.children:
            if isinstance(child, discord.ui.Button) and child.custom_id == "button_timer":
                return child
        return None
    
    def delete_files(self):
        #Prevent deleting no_cover.jpg
        if self.filename[0] != "no_cover.jpg":
            delete_temp_file(self.filename[0])
    
    def get_filenames_and_files(self,file_entry):
        if file_entry != []:
            self.filename.append(file_entry['filename'])
            self.file_path.append(file_entry['file_and_dir'])

    #Update timer label, deletion is handeld seperatly
    async def update_timer_countdown(self, duration):
        for remaining_time in range(duration, 0, -1):
            print(remaining_time)
            # Update the button label with the remaining time
            if remaining_time <=60:
                self.timer_button.label =f"{remaining_time} sec"
            else:
                self.timer_button.label =f"{remaining_time/60} min"

            await self.message.edit(view=self)  
            # Wait for 1 second
            await asyncio.sleep(1)
    
        

    @discord.ui.button(label="Correct", style=discord.ButtonStyle.green, emoji="✅", custom_id="button_correct", disabled=True)
    async def button_correct(self,button,interaction):
        original_message = interaction.message
        if interaction.message.embeds[0]:
            await interaction.response.send_message(embed=interaction.message.embeds[0])
        await original_message.delete()
        if original_message.id in scheduled_deletions:
            # Cancel the scheduled deletion task
            scheduled_deletions[original_message.id].cancel()
            del scheduled_deletions[original_message.id]
        if self.file_path != []:
            self.delete_files()
        self.stop()

    @discord.ui.button(label="Search", style=discord.ButtonStyle.primary, emoji="🔍", custom_id="button_search", disabled=True)
    async def button_search(self,button,interaction):
        original_message = interaction.message
        #If manga
        if self.search_type.lower() == "manga":
            await interaction.response.defer()
            entries = await search_entries_mangadex(self.name)
            shorten_embeds,complete_embeds,file_entries = await shorten_and_complete_embed_searchresults_mangadex(entries)
            await paginate_search(interaction,self.ctx,shorten_embeds,complete_embeds,file_entries,defer=True)

        #Is anime
        elif self.search_type.lower() == "anime":
            await interaction.response.defer()
            entries = await search_entries_anilist(self.name)
            shorten_embeds,complete_embeds = await shorten_and_complete_embed_searchresults_anilist(entries)
            await paginate_search(interaction,self.ctx,shorten_embeds,complete_embeds,defer=True)
        else:
            await interaction.response.send_message("No corresponding type found.", ephemeral= True ,delete_after=20)
        await original_message.delete()
        if original_message.id in scheduled_deletions:
            # Cancel the scheduled deletion task
            scheduled_deletions[original_message.id].cancel()
            del scheduled_deletions[original_message.id]

    @discord.ui.button(label="Dismiss", style=discord.ButtonStyle.red, emoji="✖️", custom_id="button_dismiss", disabled=True)
    async def button_dismiss(self,button,interaction):
        original_message = interaction.message
        await interaction.response.send_message("Search deleted." ,ephemeral= True ,delete_after=20)
        if original_message.id in scheduled_deletions:
            # Cancel the scheduled deletion task
            scheduled_deletions[original_message.id].cancel()
            del scheduled_deletions[original_message.id]
        await original_message.delete()
        if self.file_path != []:
            self.delete_files()
        self.stop()

    @discord.ui.button(label="", style=discord.ButtonStyle.gray, emoji="⏰", custom_id="button_timer", disabled=True)
    async def button_timer(self,button,interaction):
        await interaction.response.defer()

    


class PaginatorView(discord.ui.View):
    def __init__(self, ctx, shorten_data, complete_data, file_entries = []):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.delete_timer = 5
        self.data = shorten_data
        self.complete_data = complete_data
        self.filenames = []
        self.file_paths = []
        self.get_filenames_and_files(file_entries)
        self.current_page = 0
        self.timer_button = self.get_timer_button()
        self.prev_button = self.get_prev_button()
        self.current_page_button = self.get_current_page_button()
        self.next_button = self.get_next_button()
        self.check_for_enabled_buttons()
        self.current_page_button.label = f'{self.current_page+1}/{len(self.data)}'

    async def on_timeout(self):
        if self is not None:
            await self.message.edit(view=None)
            

    def check_for_enabled_buttons(self):
        #Disable Buttons that can not be used
        if len(self.data)-1 > 0:
            self.get_next_button().disabled = False

    def get_filenames_and_files(self,file_entries):
        if file_entries != []:
            for file_entry in file_entries:
                self.filenames.append(file_entry['filename'])
                self.file_paths.append(file_entry['file_and_dir'])


    def delete_files(self):
        # for file in self.files:
        #     file.close()
        
        for filename in self.filenames:
            # Prevent deleting no_cover.jpg
            if filename != "no_cover.jpg":
                delete_temp_file(filename)

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("You are not allowed to interact with this paginator.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green, emoji="✅", custom_id="button_accept_paginator", disabled=False)
    async def accept_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        if self.file_paths != [] and self.file_paths[self.current_page]:
            file = discord.File(self.file_paths[self.current_page])
            await interaction.response.send_message(file=file ,embed=self.complete_data[self.current_page], view=None)
            await self.message.delete()
        else:
            await interaction.response.send_message(embed=self.complete_data[self.current_page], view=None)
            await self.message.delete()

        if self.message.id in scheduled_deletions:
            # Cancel the scheduled deletion task
            scheduled_deletions[self.message.id].cancel()
            del scheduled_deletions[self.message.id]

        if self.file_paths != []:
            self.delete_files()
        self.stop()

    @discord.ui.button(label="Prev",style=discord.ButtonStyle.primary, custom_id="button_prev_paginator", disabled=True)
    async def prev_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.current_page = max(0, self.current_page - 1)
        await self.update_buttons()
        await self.update_message(interaction)

    @discord.ui.button(label="1/X",style=discord.ButtonStyle.gray, custom_id="button_current_page_paginator", disabled=True)
    async def current_page_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.defer()
        

    @discord.ui.button(label="Next",style=discord.ButtonStyle.primary, custom_id="button_next_paginator", disabled=True)
    async def next_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.current_page = min(len(self.data) - 1, self.current_page + 1)
        await self.update_buttons()
        await self.update_message(interaction)
        

    @discord.ui.button(label="Dismiss", style=discord.ButtonStyle.red, emoji="✖️", custom_id="button_dismiss_paginator", disabled=False)
    async def dismiss_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.send_message("Paginator dismissed.", ephemeral=True, delete_after=20)
        await self.message.delete()

        if self.message.id in scheduled_deletions:
            # Cancel the scheduled deletion task
            scheduled_deletions[self.message.id].cancel()
            del scheduled_deletions[self.message.id]

        if self.file_paths != []:
            self.delete_files()
        self.stop()
    
    @discord.ui.button(label="", style=discord.ButtonStyle.gray, emoji="⏰", custom_id="button_timer", disabled=True)
    async def button_timer(self,button,interaction):
        await interaction.response.defer()

    async def update_message(self,interaction):
        await interaction.response.defer()
        embed = self.data[self.current_page]
        if self.file_paths != [] and self.file_paths[self.current_page]:
            file = discord.File(self.file_paths[self.current_page])
            await self.message.edit(file = file, embed=embed,view=self)
            file.close()
        else:
            await self.message.edit(embed=embed,view=self)



    async def update_buttons(self):
        #Disable Buttons that can not be used
        self.current_page_button.label = f'{self.current_page+1}/{len(self.data)}'
        if len(self.data)-1 == 0: 
            self.prev_button.disabled = True
            self.next_button.disabled = True
        elif self.current_page == 0:
            self.prev_button.disabled = True
            self.next_button.disabled = False
        elif self.current_page == len(self.data)-1: 
            self.prev_button.disabled = False
            self.next_button.disabled = True
        else:
            self.prev_button.disabled = False
            self.next_button.disabled = False
        await self.message.edit(view=self)


    def get_prev_button(self):
        for child in self.children:
            if isinstance(child, discord.ui.Button) and child.custom_id == "button_prev_paginator":
                return child
        return None
    
    def get_current_page_button(self):
        for child in self.children:
            if isinstance(child, discord.ui.Button) and child.custom_id == "button_current_page_paginator":
                return child
        return None

    def get_next_button(self):
        for child in self.children:
            if isinstance(child, discord.ui.Button) and child.custom_id == "button_next_paginator":
                return child
        return None
    
    def get_timer_button(self):
        for child in self.children:
            if isinstance(child, discord.ui.Button) and child.custom_id == "button_timer":
                return child
        return None

#Function to delete messages after a delay (delete on timeout), default deletion time 180 = 3min
async def delete_after_delay(interaction_or_ctx,message, deletion_time = 180 , view = None):
    for remaining_time in range(deletion_time, 0, -1):
        if view:
            # Update the button label with the remaining time
            if remaining_time <=60:
                view.timer_button.label =f"{remaining_time} sec"
            else:
                minutes, seconds= divmod(remaining_time, 60)
                if seconds == 0:
                    seconds = '00'
                view.timer_button.label =f"{minutes}:{seconds} min"

            await view.message.edit(view=view)  
            # Wait for 1 second
        await asyncio.sleep(1)

    #Clear files if necessary
    if isinstance(view , PaginatorView):
        if view.file_paths != []:
            view.delete_files()
    elif isinstance(view , ButtonView):
        if view.file_path != []:
            view.delete_files()

    if message.id in scheduled_deletions:
        try:
            await interaction_or_ctx.followup.send(content= "You did not select anything. Selection dismissed.",ephemeral=True)
            await message.delete()
        except discord.NotFound:
            pass  # Message already deleted

#Paginate the shorten_embeds
async def paginate_search(interaction,ctx,shorten_embeds,complete_embeds,file_entries = [], defer = False):
    deletion_time= 180
    if file_entries != []:
        if defer:
            paginator_view = PaginatorView(ctx, shorten_embeds,complete_embeds,file_entries)
            file = discord.File(file_entries[0]['file_and_dir'])
            message = await interaction.followup.send(file = file,embed=shorten_embeds[0], view=paginator_view)
            scheduled_deletions[message.id] = asyncio.create_task(delete_after_delay(interaction,message,deletion_time,paginator_view))
            paginator_view.message = message
            file.close()
        else:
            # Not working
            paginator_view = PaginatorView(ctx, shorten_embeds,complete_embeds,file_entries)
            file = discord.File(file_entries[0]['file_and_dir'])
            await interaction.response.send_message(file = file,embed=shorten_embeds[0], view=paginator_view)
            message = await interaction.original_response()
            scheduled_deletions[message.id] = asyncio.create_task(delete_after_delay(interaction,message,deletion_time,paginator_view))
            paginator_view.message = message
            file.close()
    else:
        if defer:
            paginator_view = PaginatorView(ctx, shorten_embeds,complete_embeds)
            message = await interaction.followup.send(embed=shorten_embeds[0], view=paginator_view)
            scheduled_deletions[message.id] = asyncio.create_task(delete_after_delay(interaction,message,deletion_time,paginator_view))
            paginator_view.message = message
        else:
            # Not working
            paginator_view = PaginatorView(ctx, shorten_embeds,complete_embeds)
            await interaction.response.send_message(embed=shorten_embeds[0], view=paginator_view)
            message = await interaction.original_response()
            scheduled_deletions[message.id] = asyncio.create_task(delete_after_delay(interaction,message,deletion_time,paginator_view))
            paginator_view.message = message
    

async def search_entries_mangadex(title):
    #Using mangadex api for Webtoon and Manga
    base_url = "https://api.mangadex.org"
    max_entries = 5
    manga_params = {"title": title, **final_order_query}
    mangadex_response = requests.get(f"{base_url}/manga", params=manga_params)
    has_thumbnail:  bool = False
    
    if mangadex_response.status_code == 200:
        mangadex_data = mangadex_response.json()["data"]
        if mangadex_data:
            max_amout_of_entries = min(max_entries, len(mangadex_data))
            manga_entries = []
            for x in range(max_amout_of_entries):
                if mangadex_data[x]:
                    manga_info = mangadex_data[x]
                    id = manga_info['id']
                    cover_id = [rel['id'] for rel in manga_info['relationships'] if rel.get('type') == 'cover_art'][0]
                    series_type = manga_info['type'].capitalize()
                    title = manga_info['attributes']['title']['en']

                    #Add alternative titles
                    alt_title=''
                    alt_titles_en = [title["en"] for title in manga_info["attributes"]["altTitles"] if "en" in title]
                    alt_titles_ja_ro = [title["ja-ro"] for title in manga_info["attributes"]["altTitles"] if "ja-ro" in title]


                    for x in range(len(alt_titles_en)):
                        alt_title += alt_titles_en[x] + "\n"
                    for y in range(len(alt_titles_ja_ro)):
                        alt_title += alt_titles_ja_ro[y] + "\n"

                    description = manga_info["attributes"]["description"]["en"]
                    #Try finding cover_art over cover_id
                    mangadex_response_cover = requests.get(f"{base_url}/cover/{cover_id}")
                        
                    if mangadex_response_cover.status_code == 200:
                        manga_cover_filename = mangadex_response_cover.json()["data"]['attributes']['fileName']
                        cover_image_url = f"https://uploads.mangadex.org/covers/{id}/{manga_cover_filename}.512.jpg"
                        temp_filename = manga_cover_filename
                        temp_filename = change_filename_ending(temp_filename,cover_image_url)
                        if download_image(cover_image_url, temp_filename):
                            print("Thumbnail downloaded")
                            has_thumbnail = True
                        else:
                            print("Thumbnail could not be downloaded")
                            has_thumbnail = False
                            
                    else:
                        #Try finding cover_art with include extension of mangadex
                        mangadex_response_cover = requests.get(f"{base_url}/manga/{id}?includes[]=cover_art")
                        
                        if mangadex_response_cover.status_code == 200:
                            mangadex_data = mangadex_response_cover.json()["data"]
                            manga_cover_filename = [rel['attributes']['fileName'] for rel in mangadex_data['relationships'] if rel.get('type') == 'cover_art'][0]
                            cover_image_url = f"https://uploads.mangadex.org/covers/{id}/{manga_cover_filename}.512.jpg"
                            temp_filename = manga_cover_filename
                            temp_filename = change_filename_ending(temp_filename,cover_image_url)
                            file_and_dir = os.path.join(temp_images_directory,temp_filename)
                            if download_image(cover_image_url, temp_filename):
                                print("Thumbnail downloaded")
                                has_thumbnail = True
                            else:
                                print("Thumbnail could not be downloaded")
                                has_thumbnail = False
                                temp_filename = 'no_cover.jpg'
                                print("Using filler thumbnail")

                        else:
                            #No cover found: filler image
                            #no_cover.jpg needs to be in the root folder of the bot
                            temp_filename = 'no_cover.jpg'
                            print("Using filler thumbnail")

                    file_and_dir = os.path.join(temp_images_directory,temp_filename)
                    if alt_titles_ja_ro:
                        manga = {'id': id,'format': series_type, 'romaji_title': alt_titles_ja_ro[0], 'english_title': title, 'description': description, 'file_and_dir': file_and_dir , 'filename': temp_filename , 'has_thumbnail': has_thumbnail}
                        manga_entries.append(manga)
                    else:
                        manga = {'id': id,'format': series_type, 'romaji_title': '', 'english_title': title, 'description': description, 'file_and_dir': file_and_dir , 'filename': temp_filename , 'has_thumbnail': has_thumbnail}
                        manga_entries.append(manga)
                    
            return manga_entries
        else:
            print(f"No information found for '{title}' on MangaDex")
            return []
    else:
        print("Error accessing MangaDex API")
        return []

async def search_entries_anilist(title):
    query = '''
    query ($id: Int, $page: Int, $perPage: Int, $search: String) {
        Page (page: $page, perPage: $perPage) {
            media (id: $id, search: $search , type: ANIME) {
                id
                title {
                    romaji
                    english
                }
                format
                description
                coverImage {
                    extraLarge
                }
            }
        }
    }
    '''

    variables = {
    'search': title,
    'type' : "ANIME",
    'page': 1,
    'perPage': 10
    }

    url = 'https://graphql.anilist.co'

    response = requests.post(url, json={'query': query, 'variables': variables})
    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        data = response.json()
        animes = data["data"]["Page"]["media"]
        # Check if any media was found in the response
        if animes:
            anime_entries = []
            for anime_info in animes:
                anime_id = anime_info["id"]
                anime_format = anime_info["format"]
                romaji_title = anime_info['title']['romaji']
                english_title = anime_info['title']['english']
                description = anime_info["description"]
                cover_image_url = anime_info['coverImage']['extraLarge']
                
                anime = {'id': anime_id,'format': anime_format, 'romaji_title': romaji_title, 'english_title': english_title, 'description': description, 'cover_image_url': cover_image_url}
                anime_entries.append(anime)
            return anime_entries
    # If something went wrong or no matching media found, return None
    return []

# data is a list of entries with id,format,romaji_title,english_title,description,cover_image_url
async def shorten_and_complete_embed_searchresults_anilist(data):
    shorten_embeded_data = []
    complete_embed_data = []
    for entry in data:
        series_type = "Anime"
        if entry:
            #Correct formationg of series_type
            if entry['format']:
                #Special case of the name One-Shot
                if entry['format'].lower() == "one_shot":
                    format_correct = "One-Shot"
                else:
                    format_correct = entry['format'][0].upper() + entry['format'][1:].lower()

                series_type += "/"+ format_correct

            description_markdown = markdownify.markdownify(entry['description'])

            if entry['english_title'] == None or entry['english_title'] == '':
                entry['english_title'] = entry['romaji_title']
                entry['romaji_title'] = None

            shorten_embed = discord.Embed(title=entry['english_title'], color=0x7289da, url=f"https://anilist.co/anime/{entry['id']}")
            shorten_embed.add_field(name="Typ", value=str(series_type), inline=False)
            if entry['romaji_title'] != None:
                shorten_embed.add_field(name="Romaji Title", value=entry['romaji_title'], inline=False)
            shorten_embed.set_thumbnail(url=entry['cover_image_url'])
            shorten_embeded_data.append(shorten_embed)

            complete_embed = discord.Embed(title=entry['english_title'], description=description_markdown, color=0x7289da, url=f"https://anilist.co/anime/{entry['id']}")
            complete_embed.add_field(name="Typ", value=str(series_type), inline=False)
            if entry['romaji_title'] != None:
                complete_embed.add_field(name="Romaji Title", value=entry['romaji_title'], inline=False)
            complete_embed.set_thumbnail(url=entry['cover_image_url'])
            complete_embed_data.append(complete_embed)
        else:
            print(f"No entry found!")
    return shorten_embeded_data ,complete_embed_data

# data is a list of entries with id,format,romaji_title,english_title,description,cover_image_url
async def shorten_and_complete_embed_searchresults_mangadex(data):
    shorten_embeded_data = []
    complete_embed_data = []
    file_entries = []
    for entry in data:
        #Using Anilist API for Anime
        if entry:
            #Correct formationg of series_type
            if entry['format']:
                series_type = entry['format']
            else:
                series_type = "Manga"

            #Do not need to check for no image because if no image the default 'no_cover.jpg' will be taken
            file_and_dir = entry['file_and_dir']
            
            #file = discord.File(file_and_dir)

            filename = entry['filename']
            id = entry['id']
            shorten_embed = discord.Embed(title=entry['english_title'], color=0xffa500,url=f'https://mangadex.org/manga/{id}')
            shorten_embed.add_field(name="Typ", value=str(series_type), inline=False)
            if entry['romaji_title'] != '':
                shorten_embed.add_field(name="Alt Title", value=entry['romaji_title'], inline=False)
            
            shorten_embed.set_thumbnail(url=f'attachment://{filename}')
            shorten_embeded_data.append(shorten_embed)

            complete_embed = discord.Embed(title=entry['english_title'], description=entry['description'], color=0xffa500,url=f'https://mangadex.org/manga/{id}')
            complete_embed.add_field(name="Typ", value=str(series_type), inline=False)
            if entry['romaji_title'] != '':
                complete_embed.add_field(name="Alt Title", value=entry['romaji_title'], inline=False)
            complete_embed.set_thumbnail(url=f'attachment://{filename}')
            complete_embed_data.append(complete_embed)

            file_entry = { 'filename': filename, 'file_and_dir': file_and_dir}
            file_entries.append(file_entry)
        else:
            print(f"No entry found!")
    return shorten_embeded_data,complete_embed_data,file_entries