import re
import requests
import json
import discord
import os
from discord.ext import commands
import json
from bs4 import BeautifulSoup
import html

#To convert html to markdown
import markdownify

# Regex to match Proxer links of the form https://proxer.me/info/<number>/details#top
proxer_link_regex = r"https:\/\/proxer\.me\/info\/\d+#top"

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
    
#TODO Add option to see top 3 results
#TODO Check for biggest name comparison in json
    

class Proxer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):  
        #Check if message from bot
        if message.author.bot:
            return
        
        # Check if the message contains a Proxer link
        proxer_links = re.findall(proxer_link_regex, message.content)
        if proxer_links:
            for proxer_link in proxer_links:
                # Download the HTML source of the Proxer page
                response = requests.get(proxer_link)
                
                if response.status_code == 200:
                    html_source = response.text
                    
                    #Get Proxer ID
                    pattern = re.compile(r'https://proxer\.me/info/(\d+)#top')
                    match_id = pattern.search(proxer_link)
                    if match_id:
                        id = match_id.group(1)
                        print(f"ID: {id}")
                    else:
                        print(f"No id found in URL: {proxer_link}")
                        await message.channel.send(f"No id found in URL: {proxer_link}") 
                        return

                    
                    original_titel_regex = r"<td><b>Original Titel</b></td>\s*<td>(.*?)</td>"
                    match_original_titel = re.search(original_titel_regex, html_source)
                    
                    print(match_original_titel)
                    
                    #Check if side has original titel else assume side does not have an entry
                    if match_original_titel: 
                        original_titel = match_original_titel.group(1)
                        print(f"Found original titel: {original_titel}")

                        (english_titel,type,description,thumbnail_url) = getEntryInfo_proxer(html_source)
                        #Download Thumbnail because discord cant access it
                        download_image(thumbnail_url,temp_filename)
                        await discord_embed_proxer(message,id,original_titel,english_titel,type,description)
                        delete_temp_file(temp_filename)
                    else:
                        print(f"No titel found, abort.")
                        print(f"Check if can not be accessed because of missing rights (probably FSK18).")
                        # Unescape the HTML source
                        unescaped_html_source = html.unescape(html_source)
                        no_access_pattern = '<div id="main">\n<div class="inner"><h3>Bitte logge dich ein, um diesen Bereich betreten zu können.</h3></div>\n</div>'
                        find_error = re.search('src="/images/misc/404.png"', html_source)  
                        recaptchar_pattern = re.search('id="captcha" class="g-recaptcha"', html_source)  
                        if no_access_pattern in unescaped_html_source:
                            print(f"Can not access :'{proxer_link}', Missing permissions")
                            #TODO: Search Proxer with ID
                            ##Beispiel link für suche: https://proxer.me/search?s=search&format=raw&name=Hajirau%20Kimi%20ga%20mitai%20n%20da&sprache=alle&typ=all&status=all&taggenre=&notaggenre=&tagspoilerfilter=spoiler_0&fsk=&hide_finished=&sort=relevance&length=&length-limit=down&tags=&notags=#search
                            #Extract Name
                            #Search Name on different side depending on type
                            await message.channel.send(f"Can not access :'{proxer_link}', Missing permissions") 
                        elif find_error:
                            print("Page not found 404.")   
                            await message.channel.send(f"No existing entry with id = {id} : '{proxer_link}'") 
                        elif recaptchar_pattern:
                            #Not tested yet
                            print("Recaptchar please wait a bit.")   
                            await message.channel.send(f"Proxer blocked us with a recaptchar, please wait a bit befor sending more links. Blocked link: '{proxer_link}'") 
                        else:
                            await message.channel.send(f"#1 Unknow error with : '{proxer_link}'") 
                else:
                    await message.channel.send(f"#2 Unknown error with : '{proxer_link}'") 

#TODO
#Add Send function for embed: add support possibility for thumbnail, markdown

async def discord_embed_proxer(message, id , original_titel, alternative_titel, type, description):
    file = discord.File(temp_filename) 
    embed = discord.Embed(title=original_titel, description=description, color=0x992d22,url=f"https://proxer.me/info/{id}#top")
    embed.add_field(name="Typ", value=type, inline=False)
    embed.add_field(name="Alternative Title", value=alternative_titel, inline=False)
    embed.set_thumbnail(url=f'attachment://{temp_filename}')
    await message.channel.send(file=file,embed = embed)



def getEntryInfo_proxer(html_source)-> (str,str,str,str):

    english_titel_regex = r"<td><b>Englischer Titel</b></td>\s*<td>(.*?)</td>"
    match_english_titel = re.search(english_titel_regex, html_source)

    if match_english_titel:
        english_titel = match_english_titel.group(1)
        print(f"Found english titel: {english_titel}")
    else:
        print(f"No english titel")
    
    # Determine the type (Anime, Webtoon, Manga, OVA,...) based on the HTML source
    type_pattern = r'<span class="fn">(.*?)</span> \((.*?)\):'
    match_type = re.search(type_pattern, html_source)

    #Maybe use Error Handler?
    if match_type:
        type = match_type.group(2).strip()
        print(f"Type was found: {type}")
    else:
        type = "Unknown"
        print(f"Type not found!")

    #Extract description
    # Parse the HTML source
    soup = BeautifulSoup(html_source, 'html.parser')
    # Find the desired text within the specific <td> element
    description = soup.find('td', {'colspan': '2'}).text.strip()
    if not description:
        description = "Description could not be found."
    else:
        description = markdownify.markdownify(description)
        print("Description was found.")
    
    #Get Thumbnail
    # Define a regular expression pattern
    pattern = re.compile(r'src="//cdn\.proxer\.me/cover/(\d+)\.(jpg|png)"')
    

    # Find all matches in the HTML source
    match = pattern.search(html_source)
    thumbnail_url = ""
    if match:
        thumb_id = match.group(1)
        thumb_extension = match.group(2)
        thumbnail_url = f"https://cdn.proxer.me/cover/{thumb_id}.{thumb_extension}"
        print(thumbnail_url)
        

    return english_titel,type,description,thumbnail_url


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
            romaji_title = anime_info['title']['romaji']
            english_title = anime_info['title']['english']
            description = anime_info["description"]
            cover_image_url = anime_info['coverImage']['extraLarge']

            return {
                'id': anime_id,
                'romaji_title': romaji_title,
                'english_title': english_title,
                'description': description,
                'cover_image_url': cover_image_url,
            }

    # If something went wrong or no matching media found, return None
    return None
    
# def anilist():
#     # Determine the type (Anime, Webtoon, Manga) based on the HTML source
#                     if re.search(r"Animeserie/TV", html_source):
#                         #Using Anilist API for Anime
#                         series_type = "Anime"
#                         anime_info = search_anime_info(english_titel)

#                         if anime_info:
#                             description_markdown = markdownify.markdownify(anime_info['description'])
#                             embed = discord.Embed(title=anime_info['english_title'], description=description_markdown, color=0x7289da, url=f"https://anilist.co/anime/{anime_info['id']}")
#                             embed.add_field(name="Typ", value=str(series_type), inline=False)
#                             embed.add_field(name="Romaji Title", value=anime_info['romaji_title'], inline=False)
#                             embed.set_thumbnail(url=anime_info['cover_image_url'])

#                             await message.channel.send(embed = embed)
#                         else:
#                             #If no titel was found under the english_titel try the original_titel
#                             anime_info = search_anime_info(original_titel)
#                             if anime_info:
#                                 description_markdown = markdownify.markdownify(anime_info['description'])
#                                 embed = discord.Embed(title=anime_info['english_title'], description=description_markdown, color=0x7289da,url=f"https://anilist.co/anime/{anime_info['id']}")
#                                 embed.add_field(name="Typ", value=str(series_type), inline=False)
#                                 embed.add_field(name="Romaji Title", value=anime_info['romaji_title'], inline=False)
#                                 embed.set_thumbnail(url=anime_info['cover_image_url'])
#                                 await message.channel.send(embed = embed)
#                             else:
#                                 await message.channel.send(f"No information found for '{english_titel}'")

# def mangadex():
#     #Using mangadex api for Webtoon and Manga
#                         series_type = "Webtoon" if "Webtoon" in html_source else "Manga"
#                         base_url = "https://api.mangadex.org"
#                         manga_params = {"title": english_titel, **final_order_query}
#                         mangadex_response = requests.get(f"{base_url}/manga", params=manga_params)
#                         has_thumbnail:  bool = False
                        
#                         if mangadex_response.status_code == 200:
#                             mangadex_data = mangadex_response.json()["data"]
#                             manga_info = mangadex_data[0] if mangadex_data else None
#                             if manga_info:
#                                 id = manga_info['id']
#                                 cover_id = [rel['id'] for rel in manga_info['relationships'] if rel.get('type') == 'cover_art'][0]
#                                 title = manga_info['attributes']['title']['en']

#                                 description = manga_info["attributes"]["description"]["en"]
#                                 #Try finding cover_art over cover_id
#                                 mangadex_response_cover = requests.get(f"{base_url}/cover/{cover_id}")
                                    
#                                 if mangadex_response_cover.status_code == 200:
#                                     manga_cover_filename = mangadex_response_cover.json()["data"]['attributes']['fileName']
#                                     cover_image_url = f"https://uploads.mangadex.org/covers/{id}/{manga_cover_filename}.512.jpg"
#                                     temp_filename = change_filename_ending(temp_filename,cover_image_url)
#                                     if download_image(cover_image_url, temp_filename):
#                                         print("Thumbnail downloaded")
#                                         has_thumbnail = True
#                                     else:
#                                         print("Thumbnail could not be downloaded: #1")
#                                         has_thumbnail = False
                                        
#                                 else:
#                                     #Try finding cover_art with include extension of mangadex
#                                     mangadex_response_cover = requests.get(f"{base_url}/manga/{id}?includes[]=cover_art")
                                    
#                                     if mangadex_response_cover.status_code == 200:
#                                         mangadex_data = mangadex_response_cover.json()["data"]
#                                         manga_cover_filename = [rel['attributes']['fileName'] for rel in mangadex_data['relationships'] if rel.get('type') == 'cover_art'][0]
#                                         cover_image_url = f"https://uploads.mangadex.org/covers/{id}/{manga_cover_filename}.512.jpg"
#                                         temp_filename = change_filename_ending(temp_filename,cover_image_url)
#                                         if download_image(cover_image_url, temp_filename):
#                                             print("Thumbnail downloaded")
#                                             has_thumbnail = True
#                                         else:
#                                             print("Thumbnail could not be downloaded: #1")
#                                             has_thumbnail = False
                                    
#                                     else:
#                                         #No cover found: filler image
#                                         #no_cover.jpg needs to be in the root folder of the bot
#                                         temp_filename = 'no_cover.jpg'
#                                         print("Using filler thumbnail")
#                                         # if download_image(cover_image_url, temp_filename):
#                                             # has_thumbnail = True
#                                             # print("Filler thumbnail downloaded")
#                                         # else:
#                                             # print("Thumbnail could not be downloaded: #2")
#                                             # has_thumbnail = False
                                
#                                 #Try get alternative title
#                                 if english_titel != title:
#                                     alt_title = english_titel
#                                 elif original_titel != title:
#                                     alt_title = original_titel
#                                 else:
#                                     alt_title = title
                                
#                                 if has_thumbnail:
#                                     file = discord.File(temp_filename)  
#                                     embed = discord.Embed(title=title, description=description, color=0x7289da,url=f'https://mangadex.org/manga/{id}')
#                                     embed.add_field(name="Typ", value=str(series_type), inline=False)
#                                     embed.add_field(name="Alt Title", value=alt_title, inline=False)
#                                     embed.set_thumbnail(url=f'attachment://{temp_filename}')
#                                     await message.channel.send(file=file,embed = embed)
#                                     #Prevent deleting no_cover.jpg
#                                     if temp_filename != "no_cover.jpg":
#                                         delete_temp_file(temp_filename)
#                                 else:
#                                     embed = discord.Embed(title=title, description=description, color=0x7289da,url=f'https://mangadex.org/manga/{id}')
#                                     embed.add_field(name="Typ", value=str(series_type), inline=False)
#                                     embed.add_field(name="Alt Title", value=alt_title, inline=False)
#                                     await message.channel.send(embed = embed)
                                
                                
#                             else:
#                                 await message.channel.send(f"No information found for '{english_titel}' on MangaDex")
#                         else:
#                             await message.channel.send("Error accessing MangaDex API")

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