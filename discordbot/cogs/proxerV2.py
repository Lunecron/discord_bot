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
proxer_link_regex = r'https://proxer\.me/info/(\d+)(/[a-zA-Z0-9_]+)?(#top)?'

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
    
#TODO Add option to see top 3 results
#TODO Check for biggest name comparison in json
    

class Proxer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        createImageDir()

    @commands.Cog.listener()
    async def on_message(self, message):  
        #Check if message from bot
        if message.author.bot:
            return
        
        # Check if the message contains a Proxer link
        proxer_links = detect_proxer_links(message.content)
        if proxer_links:
            for proxer_link in proxer_links:

                # Check if proxer_link is a string
                if not isinstance(proxer_link, str):
                    print(f"Skipping non-string element: {proxer_link}")
                    return
                
                #Get Proxer ID
                proxer_id = extract_proxer_id(proxer_link)

                if proxer_id:
                    id = proxer_id
                    print(f"ID: {id}")
                    proxer_link = f"https://proxer.me/info/{id}#top"
                else:
                    print(f"No id found in URL: {proxer_link}")
                    await message.channel.send(f"No id found in URL: {proxer_link}") 
                    return
                
                
                # Download the HTML source of the Proxer page
                response = requests.get(proxer_link)
                
                if response.status_code == 200:
                    html_source = response.text
                    
                    original_titel_regex = r"<td><b>Original Titel</b></td>\s*<td>(.*?)</td>"
                    match_original_titel = re.search(original_titel_regex, html_source)
                    
                    print(match_original_titel)
                    
                    #Check if side has original titel else assume side does not have an entry
                    if match_original_titel: 
                        original_titel = match_original_titel.group(1)
                        print(f"Found original titel: {original_titel}")

                        (english_titel,type,description,adaption_id,adaption_name,thumbnail_url) = getEntryInfo_proxer(html_source)
                        #Download Thumbnail because discord cant access it
                        download_image(thumbnail_url,temp_filename)
                        await discord_embed_proxer(message,id,original_titel,english_titel,type,description,adaption_id,adaption_name)
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
                            #Maybe add recaptcha solver?
                            print("Recaptchar please wait a bit.")   
                            await message.channel.send(f"Proxer blocked us with a recaptchar, please wait a bit befor sending more links. Blocked link: '{proxer_link}'") 
                        else:
                            await message.channel.send(f"#1 Unknow error with : '{proxer_link}'") 
                else:
                    await message.channel.send(f"#2 Unknown error with : '{proxer_link}'") 

#TODO
#Add Send function for embed: add support possibility for thumbnail, markdown

async def discord_embed_proxer(message, id , original_titel, alternative_titel, type, description, adaption_id,adaption_name):
    file_and_dir = os.path.join(temp_images_directory,temp_filename)
    file = discord.File(file_and_dir) 
    embed = discord.Embed(title=original_titel, description=description, color=0x992d22,url=f"https://proxer.me/info/{id}#top")
    embed.add_field(name="Typ", value=type, inline=False)
    if alternative_titel != '' and alternative_titel != original_titel:
        embed.add_field(name="Alternative Title", value=alternative_titel, inline=False)
    if adaption_id != '':
        adaption_url = f" https://proxer.me/{adaption_id}/details#top"
        embed.add_field(name="Adaption of",value=f"[{adaption_name}]({adaption_url})", inline=True)
    embed.set_thumbnail(url=f'attachment://{temp_filename}')
    await message.channel.send(file=file,embed = embed)
    file.close()

def detect_proxer_links(message):
    # Define the regex pattern for Proxer links
    pattern = re.compile(r'(https://proxer\.me/(chapter|info|read)/(\d+))')

    # Find all matches in the message
    matches = re.findall(pattern, message)
    links = []
    for match in matches:
        links.append(match[0])
    return links

def extract_proxer_id(link : str):
    # Define the regex pattern to extract the ID
    pattern = re.compile(r'https://proxer\.me/(chapter|info|read)/(\d+)')

    # Find the match in the link
    match = pattern.search(link)

    if match:
        # Extract and return the ID
        return match.group(2)
    else:
        # Return None if no match is found
        return None

def getEntryInfo_proxer(html_source)-> (str,str,str,str,str,str):

    english_titel_regex = r"<td><b>Englischer Titel</b></td>\s*<td>(.*?)</td>"
    match_english_titel = re.search(english_titel_regex, html_source)
    english_titel = ''
    if match_english_titel:
        english_titel = match_english_titel.group(1)
        print(f"Found english titel: {english_titel}")
    else:
        print(f"No english titel")
    
    # Determine the type (Anime, Webtoon, Manga, OVA,...) based on the HTML source
    type_pattern = r'<span class="fn">(.*?)</span> \((.*?)\):'
    match_type = re.search(type_pattern, html_source)
    type =''
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
    

    #Find adaptions
    adaption_titel_regex = r'<tr>\s*<td valign="top"><b>Adaption</b></td>\s*<td valign="top"><a href="/info/(\d+)">(.*?)</a></td>\s*</tr>'
    match_adaption = re.search(adaption_titel_regex, html_source)
    if match_adaption:
        adaption_id = match_adaption.group(1)
        adaption_name = match_adaption.group(2)

    else:
        adaption_id = ''
        adaption_name =''
        print("No Adaption found.")


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
        

    return english_titel,type,description,adaption_id,adaption_name,thumbnail_url


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

def setup(bot):
    bot.add_cog(Proxer(bot))