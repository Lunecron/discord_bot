import re
import requests
import json
import discord
import os
from discord.ext import commands
import json
import jmespath

# Regex to match Proxer links of the form https://proxer.me/info/<number>/details#top
proxer_link_regex = r"https:\/\/proxer\.me\/info\/\d+#top"


#Sorting for mangadex
order = {
    "relevance": "desc",
    "followedCount": "desc",
}
final_order_query = {}
# { "order[rating]": "desc", "order[followedCount]": "desc" }
for key, value in order.items():
    final_order_query[f"order[{key}]"] = value
    
#TODO Add option to see top 3 results
#TODO Check for biggest name comparison in json
    

class Proxer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):  
        # Check if the message contains a Proxer link
        proxer_links = re.findall(proxer_link_regex, message.content)
        if proxer_links:
            for proxer_link in proxer_links:
                # Download the HTML source of the Proxer page
                response = requests.get(proxer_link)
                html_source = response.text
                temp_filename= "temp.jpg"
                
                # Extract the value of the "Englischer Titel" row from the HTML source
                original_titel_regex = r"<td><b>Original Titel</b></td>\s*<td>(.*?)</td>"
                match_original_titel = re.search(original_titel_regex, html_source)
                original_titel = match_original_titel.group(1)
                
                english_titel_regex = r"<td><b>Englischer Titel</b></td>\s*<td>(.*?)</td>"
                match_english_titel = re.search(english_titel_regex, html_source)
                if match_english_titel:
                    english_titel = match_english_titel.group(1)
                    print(f"Found Englischer Titel: {english_titel}")

                    # Determine the type (Anime, Webtoon, Manga) based on the HTML source
                    if re.search(r"Animeserie/TV", html_source):
                        series_type = "Anime"
                        anime_info = search_anime_info(english_titel)

                        if anime_info:
                            embed = discord.Embed(title=anime_info['english_title'], description=anime_info['description'], color=0x7289da)
                            embed.add_field(name="Typ", value=str(series_type), inline=False)
                            embed.add_field(name="Romaji Title", value=anime_info['romaji_title'], inline=False)
                            embed.set_thumbnail(url=anime_info['cover_image_url'])

                            await ctx.send(embed=embed)
                        else:
                            await ctx.send(f"No information found for '{english_titel}'")

                    elif re.search(r"Mangaserie/Webtoon", html_source) or re.search(r"Mangaserie", html_source):
                        series_type = "Webtoon" if "Webtoon" in html_source else "Manga"
                        base_url = "https://api.mangadex.org"
                        manga_params = {"title": english_titel, **final_order_query}
                        mangadex_response = requests.get(f"{base_url}/manga", params=manga_params)
                        has_thumbnail:  bool = False
                        
                        print(mangadex_response.status_code == 200)
                        if mangadex_response.status_code == 200:
                            mangadex_data = mangadex_response.json()["data"]
                            manga_info = mangadex_data[0]
                            if manga_info:
                                id = manga_info['id']
                                cover_id = [rel['id'] for rel in manga_info['relationships'] if rel.get('type') == 'cover_art'][0]
                                title = manga_info['attributes']['title']['en']
                                description = manga_info["attributes"]["description"]["en"]
                                #Try finding cover_art over cover_id
                                mangadex_response_cover = requests.get(f"{base_url}/cover/{cover_id}")
                                   
                                if mangadex_response_cover.status_code == 200:
                                    manga_cover_filename = mangadex_response_cover.json()["data"]['attributes']['fileName']
                                    cover_image_url = f"https://uploads.mangadex.org/covers/{id}/{manga_cover_filename}"
                                    temp_filename = change_filename_ending(temp_filename,cover_image_url)
                                    if download_image(cover_image_url, temp_filename):
                                        print("Thumbnail downloaded")
                                        has_thumbnail = True
                                    else:
                                        print("Thumbnail could not be downloaded: #1")
                                        has_thumbnail = False
                                        
                                else:
                                    #Try finding cover_art with include extension of mangadex
                                    mangadex_response_cover = requests.get(f"{base_url}/manga/{id}?includes[]=cover_art")
                                    print(mangadex_response_cover.status_code)
                                    
                                    if mangadex_response_cover.status_code == 200:
                                        mangadex_data = mangadex_response_cover.json()["data"]
                                        manga_cover_filename = [rel['attributes']['fileName'] for rel in mangadex_data['relationships'] if rel.get('type') == 'cover_art'][0]
                                        cover_image_url = f"https://uploads.mangadex.org/covers/{id}/{manga_cover_filename}"
                                        temp_filename = change_filename_ending(temp_filename,cover_image_url)
                                        print(cover_image_url)
                                        print(temp_filename)
                                        if download_image(cover_image_url, temp_filename):
                                            print("Thumbnail downloaded")
                                            has_thumbnail = True
                                        else:
                                            print("Thumbnail could not be downloaded: #1")
                                            has_thumbnail = False
                                    
                                    else:
                                        #No cover found: filler image
                                        #no_cover.jpg needs to be in the root folder of the bot
                                        temp_filename = 'no_cover.jpg'
                                        print("Using filler thumbnail")
                                        # if download_image(cover_image_url, temp_filename):
                                            # has_thumbnail = True
                                            # print("Filler thumbnail downloaded")
                                        # else:
                                            # print("Thumbnail could not be downloaded: #2")
                                            # has_thumbnail = False
                                
                                #Try get alternative title
                                if english_titel != title:
                                    alt_title = english_titel
                                elif original_titel != title:
                                    alt_title = original_titel
                                else:
                                    alt_title = title
                                
                                if has_thumbnail:
                                    file = discord.File(temp_filename)  
                                    embed = discord.Embed(title=title, description=description, color=0x7289da,url=f'https://mangadex.org/manga/{id}')
                                    embed.add_field(name="Typ", value=str(series_type), inline=False)
                                    embed.add_field(name="Alt Title", value=alt_title, inline=False)
                                    embed.set_thumbnail(url='attachment://temp.jpg')
                                    await message.channel.send(file=file,embed = embed)
                                    #Prevent deleting no_cover.jpg
                                    if temp_filename != "no_cover.jpg":
                                        delete_temp_file(temp_filename)
                                else:
                                    embed = discord.Embed(title=title, description=description, color=0x7289da,url=f'https://mangadex.org/manga/{id}')
                                    embed.add_field(name="Typ", value=str(series_type), inline=False)
                                    embed.add_field(name="Alt Title", value=alt_title, inline=False)
                                    await message.channel.send(embed = embed)
                                
                                
                            else:
                                await message.channel.send(f"No information found for '{english_titel}' on MangaDex")
                        else:
                            await message.channel.send("Error accessing MangaDex API")
                    else:
                        series_type = "Unknown"
                        api_url = ""
                        # Create an embed with the information from the API
                        embed = discord.Embed(title=english_titel, type="rich", description=f"{series_type}: {english_titel}")
                        await message.channel.send(embed=embed)

                else:
                    print("Could not find Englischer Titel in HTML source")          
                    
                    
def search_anime_info(title):
    query = '''
    query ($search: String) {
      Media (search: $search, type: ANIME) {
        id
        title {
          romaji
          english
        }
        description
        coverImage {
          extraLarge
        }
      }
    }
    '''

    variables = {
        'search': title
    }

    url = 'https://graphql.anilist.co'

    response = requests.post(url, json={'query': query, 'variables': variables})

    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        data = response.json()
        media = data.get('data', {}).get('Media')

        # Check if any media was found in the response
        if media:
            anime_info = media[0]
            romaji_title = anime_info['title']['romaji']
            english_title = anime_info['title']['english']
            description = anime_info.get('description', 'No description available')
            cover_image_url = anime_info['coverImage']['extraLarge']

            return {
                'romaji_title': romaji_title,
                'english_title': english_title,
                'description': description,
                'cover_image_url': cover_image_url,
            }

    # If something went wrong or no matching media found, return None
    return None
    
    
#delete temp image
def delete_temp_file(temp_filename)-> None:
    try:
        os.remove(temp_filename)
        print(f"Temporary file {temp_filename} deleted.")
    except Exception as e:
        print(f"Error deleting temporary file: {e}")

#download image for thumbnail
def download_image(url, temp_filename)-> bool:
    response = requests.get(url)
    print(response.status_code)
    if response.status_code == 200:
        with open(temp_filename, 'wb') as f:
            f.write(response.content)
        return True
    else:
        return False

#download json file for request testing
def download_file(data):
    with open("data.json", 'w') as json_file:
            json.dump(data, json_file, indent=4)
        
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

def setup(bot):
    bot.add_cog(Proxer(bot))