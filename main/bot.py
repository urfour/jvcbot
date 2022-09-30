import string
import nextcord
import locale
import requests
import unidecode
import pandas as pd

locale.setlocale(locale.LC_ALL, 'fr_FR.UTF-8')

from bs4 import BeautifulSoup
from datetime import datetime
from nextcord import ButtonStyle, Embed, Color
from nextcord.ext import commands
from nextcord.ui import Button, View, Select
from dotenv import load_dotenv
from os import getenv

load_dotenv()

TOKEN = getenv("DISCORD_TOKEN")
DESCRIPTION = '''Bot permettant d'interagir avec les topics du forum Blabla 18 - 25 ans'''
URL = 'https://www.jeuxvideo.com/forums'
    
intents = nextcord.Intents.all()
bot = commands.Bot(description=DESCRIPTION, intents=intents)

def get_topics(page_nb):
    page = requests.get(f'{URL}/0-51-0-1-0-{1+25*(page_nb)}-0-blabla-18-25-ans.htm')
    soup = BeautifulSoup(page.text, 'html.parser')

    topics = soup.find('ul', {'class': 'topic-list'}).find_all('li')[1:]

    subjects = []
    urls = []
    authors = []
    nb_msgs = []
    dates = []

    for topic in topics[2:]:
        try:
            subject = topic.find('span', {'class': 'topic-subject'}).a['title']
            url = topic.find('span', {'class': 'topic-subject'}).a['href']
            author = topic.find_all('span')[1].get_text().strip()
            nb_msg = topic.find('span', {'class': 'topic-count'}).get_text().strip()
            date = topic.find('span', {'class': 'topic-date'}).get_text().strip()
            try:
                date = datetime.strptime(date, '%d/%m/%Y')
            except:
                try:
                    date = datetime.strptime(f'{datetime.now().strftime("%d/%m/%Y")} {date}', "%d/%m/%Y %H:%M:%S")
                except:
                    print(f"Impossible de parser la date suivante : {date}")
        except:
            continue

        subjects.append(subject)
        urls.append(url)
        authors.append(author)
        nb_msgs.append(nb_msg)
        dates.append(date)

    df_topics = pd.DataFrame({'Date': dates, 'Auteur': authors, 'Titre': subjects, 'Lien': urls, 'Messages': nb_msgs})
    dropdown_options = [nextcord.SelectOption(description=f"[{datetime.strftime(topic['Date'], '%H:%M:%S')}] {topic['Auteur']}", label=topic['Titre'], value=topic['Lien'][8:30]) for _, topic in df_topics.iterrows()]
    dropdown = Select(placeholder='Choisissez le topic à afficher', options=dropdown_options)
    return dropdown

@bot.event
async def on_ready():
    print(f'Connecté en tant que {bot.user} (ID : {bot.user.id})')
    print('------')

@bot.slash_command()
async def topics(ctx):
    """
    Affiche tous les topics de la page choisie
    """
    current_page = 0
    
    async def dropdown_callback(interaction : nextcord.Interaction):
        selected_option = -1
        for option in dropdown.options:
            if option.value == dropdown.values[0]:
                selected_option = option
        url = (
            f"{URL}/{selected_option.value}-"
            + unidecode.unidecode(selected_option.label).lower().translate(str.maketrans('', '', string.punctuation)).strip().replace(' ', '-')
            + ".htm"
        )

        async def share_callback(interaction : nextcord.Interaction):
            nonlocal url
            await interaction.response.send_message(url)

        share_button = Button(label="Partager", style=ButtonStyle.blurple)
        share_button.callback = share_callback
        dropdown_view = View(timeout=180)
        dropdown_view.add_item(share_button)

        page = requests.get(url)
        soup = BeautifulSoup(page.text, 'html.parser')

        messages = soup.find_all('div', {'class': 'bloc-message-forum'})

        try:
            embed = Embed(title=f'(_prévisualisation_) {selected_option.label}', color=Color.orange())
            for message in messages:
                header = message.find('div', {'class': 'bloc-header'})
                nick = header.span.get_text().strip()
                date = header.find('span', {'class': 'lien-jv'}).getText()
                content = message.find('div', {'class': 'bloc-contenu'}).find('div').getText()

                embed.add_field(name=f"Publié par {nick} le {date}", value=content, inline=False)
            await interaction.response.send_message(embed=embed, view=dropdown_view, ephemeral=True)
        except:
            await interaction.response.send_message(
                content=f"Les messages sont trop longs pour être affichés, rendez-vous directement sur le topic : {url}", 
                view=dropdown_view, 
                ephemeral=True
            )

    async def next_callback(interaction):
        nonlocal current_page, sent_msg, dropdown
        current_page += 1
        my_view.remove_item(dropdown)
        dropdown = get_topics(page_nb=current_page)
        dropdown.callback = dropdown_callback
        my_view.add_item(dropdown)
        await sent_msg.edit(f"Page {current_page+1}", view=my_view)

    async def refresh_callback(interaction):
        nonlocal current_page, sent_msg, dropdown
        my_view.remove_item(dropdown)
        dropdown = get_topics(page_nb=current_page)
        dropdown.callback = dropdown_callback
        my_view.add_item(dropdown)
        await sent_msg.edit(f"Page {current_page+1}", view=my_view)

    async def previous_callback(interaction):
        nonlocal current_page, sent_msg, dropdown
        if current_page > 0:
            current_page -= 1
            my_view.remove_item(dropdown)
            dropdown = get_topics(page_nb=current_page)
            dropdown.callback = dropdown_callback
            my_view.add_item(dropdown)
            await sent_msg.edit(f"Page {current_page+1}", view=my_view)


    previous_button = Button(label="<", style=ButtonStyle.blurple)
    previous_button.callback = previous_callback

    refresh_button = Button(label="Actualiser", style=ButtonStyle.blurple)
    refresh_button.callback = refresh_callback

    next_button = Button(label=">", style=ButtonStyle.blurple)
    next_button.callback = next_callback

    dropdown = get_topics(page_nb=0)
    dropdown.callback = dropdown_callback

    my_view = View(timeout=600)
    my_view.add_item(dropdown)
    my_view.add_item(previous_button)
    my_view.add_item(refresh_button)
    my_view.add_item(next_button)
    sent_msg = await ctx.send(f"Page 1", view=my_view, ephemeral=True)

if __name__ == '__main__':
    bot.run(TOKEN)