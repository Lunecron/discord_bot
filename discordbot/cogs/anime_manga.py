import re
import requests
import json
import discord
import os
from discord.ext import commands
from discord.commands import Option
import json
from bs4 import BeautifulSoup
import time

#To convert html to markdown
import markdownify

#Directory of the main file of the bot
bot_main_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
temp_images_directory = os.path.join(bot_main_directory, 'temp_images')

temp_filename= "temp.jpg"

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

    @commands.slash_command(description="Page example")
    async def paginate(self, ctx):
        # Replace this with your list of embeds or messages
        data = [discord.Embed(title=f"Page {i}", description=f"Content of page {i}") for i in range(1, 6)]

        await paginate_search(ctx,data)

def setup(bot) -> None:
    bot.add_cog(AnimeAndManga(bot))

async def anilist(ctx,name : str):
    #Using Anilist API for Anime
    series_type = "Anime"
    anime_info = search_anime_info(name)

    if anime_info:
        description_markdown = markdownify.markdownify(anime_info['description'])
        
        #Correct formationg os series_type
        if anime_info['format']:
            #Special case of the name One-Shot
            if anime_info['format'].lower() == "one_shot":
                format_correct = "One-Shot"
            else:
                format_correct = anime_info['format'][0].upper() + anime_info['format'][1:].lower()

            series_type += "/"+ format_correct



        embed = discord.Embed(title=anime_info['english_title'], description=description_markdown, color=0x7289da, url=f"https://anilist.co/anime/{anime_info['id']}")
        embed.add_field(name="Typ", value=str(series_type), inline=False)
        embed.add_field(name="Romaji Title", value=anime_info['romaji_title'], inline=False)
        embed.set_thumbnail(url=anime_info['cover_image_url'])
        button_view = ButtonView(ctx)
        await ctx.followup.send(embed = embed, view=button_view()) 
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
                embed = discord.Embed(title=title, description=description, color=0x7289da,url=f'https://mangadex.org/manga/{id}')
                embed.add_field(name="Typ", value=str(series_type), inline=False)
                if alt_title != '':
                    embed.add_field(name="Alt Title", value=alt_title, inline=False)
                embed.set_thumbnail(url=f'attachment://{temp_filename}')
                
                button_view = ButtonView(ctx)
                await ctx.followup.send(file=file, embed=embed , view=button_view)
                # Enable the button after 1 second
                await button_view.enable_after_delay()
                file.close()
                #Prevent deleting no_cover.jpg
                if temp_filename != "no_cover.jpg":
                    delete_temp_file(temp_filename)
            else:
                embed = discord.Embed(title=title, description=description, color=0x7289da,url=f'https://mangadex.org/manga/{id}')
                embed.add_field(name="Typ", value=str(series_type), inline=False)
                embed.add_field(name="Alt Title", value=alt_title, inline=False)
                button_view = ButtonView(ctx)
                await ctx.followup.send(embed = embed, view=button_view) 
                # Enable the button after 1 second
                await button_view.enable_after_delay()
            
            
        else:
            await ctx.followup.send(f"No information found for '{name}' on MangaDex", ephemeral= True)
    else:
        await ctx.followup.send("Error accessing MangaDex API", ephemeral= True)

#delete temp image
def delete_temp_file(temp_filename)-> None:
    file_and_dir = os.path.join(temp_images_directory,temp_filename)
    time.sleep(5)
    try:
        os.remove(file_and_dir)
        print(f"Temporary file {temp_filename} deleted.")
    except Exception as e:
        print(f"Error deleting temporary file ({temp_filename}): {e}")

#download image for thumbnail
def download_image(url, temp_filename) -> bool:
    file_and_dir = os.path.join(temp_images_directory,temp_filename)
    response = requests.get(url)
    if response.status_code == 200:
        with open(file_and_dir, 'wb') as f:
            f.write(response.content)
        f.close() # Close the file explicitly
        response.close()  # Close the response explicitly
        return True
    else:
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

    def __init__(self,ctx):
        super().__init__(timeout=None)
        self.ctx = ctx

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
            if isinstance(child, discord.ui.Button):
                child.disabled = False
        await self.message.edit(view=self)
        

    @discord.ui.button(label="Correct", style=discord.ButtonStyle.green, emoji="✅", custom_id="button_correct", disabled=True)
    async def button_correct(self,button,interaction):
        original_message = interaction.message
        if interaction.message.embeds[0]:
            await interaction.response.send_message(embed=interaction.message.embeds[0])
        await original_message.delete()

    @discord.ui.button(label="Search", style=discord.ButtonStyle.primary, emoji="🔍", custom_id="button_search", disabled=True)
    async def button_search(self,button,interaction):
        await interaction.response.send_message("Hello")

    @discord.ui.button(label="Dismiss", style=discord.ButtonStyle.red, emoji="✖️", custom_id="button_dismiss", disabled=True)
    async def button_dismiss(self,button,interaction):
        original_message = interaction.message
        await interaction.response.send_message("Search deleted." ,ephemeral= True ,delete_after=20)
        await original_message.delete()


class PaginatorView(discord.ui.View):
    def __init__(self, ctx, data):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.data = data
        self.current_page = 0

    async def on_timeout(self):
        if self is not None:
            await self.message.edit(view=None)

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("You are not allowed to interact with this paginator.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green, emoji="✅", custom_id="button_accept_paginator", disabled=False)
    async def accept_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.send_message(embed=self.data[self.current_page], view=None)
        await self.message.delete()

    @discord.ui.button(label="Prev",style=discord.ButtonStyle.primary, custom_id="button_prev_paginator", disabled=False)
    async def prev_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.current_page = max(0, self.current_page - 1)
        await self.update_message(interaction)

    @discord.ui.button(label="Next",style=discord.ButtonStyle.primary, custom_id="button_next_paginator", disabled=False)
    async def next_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.current_page = min(len(self.data) - 1, self.current_page + 1)
        await self.update_message(interaction)

    @discord.ui.button(label="Dismiss", style=discord.ButtonStyle.red, emoji="✖️", custom_id="button_dismiss_paginator", disabled=False)
    async def dismiss_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.send_message("Paginator dismissed.", ephemeral=True)
        await self.message.delete()

    async def update_message(self,interaction):
        await interaction.response.defer()
        embed = self.data[self.current_page]
        await self.message.edit(embed=embed)


#Paginate the embedlist data
async def paginate_search(ctx,data):
    paginator_view = PaginatorView(ctx, data)
    message = await ctx.respond(embed=data[0], view=paginator_view)
    paginator_view.message = message