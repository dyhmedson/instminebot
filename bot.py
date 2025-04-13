import os
import time
import requests
from threading import Thread
from flask import Flask
from bs4 import BeautifulSoup
from telegram import Update, InlineQueryResultAudio
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    InlineQueryHandler,
)

# === FLASK APP PARA KEEP-ALIVE ===
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Bot está vivo!"

def run_web():
    web_app.run(host='0.0.0.0', port=8080)

# === FUNÇÃO PARA BUSCAR NO MYINSTANTS ===
def search_myinstants(query):
    url = f"https://www.myinstants.com/search/?name={query}"
    response = requests.get(url)

    if response.status_code != 200:
        print("Erro ao acessar o site MyInstants.")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')
    buttons = soup.find_all('button', class_='small-button')

    results = []
    for button in buttons:
        audio_name = button['title'].replace("Play ", "").strip()
        onclick_value = button['onclick']
        audio_path = onclick_value.split("'")[1]
        full_audio_url = f"https://www.myinstants.com{audio_path}"
        results.append((audio_name, full_audio_url))
        print(f"Áudio encontrado: {audio_name} - {full_audio_url}")

    return results

# === HANDLERS ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Olá! Eu sou o MyInstantsBot. Use /search <palavra-chave> para buscar sons ou digite @instminebot no modo inline!"
    )

async def send_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = ' '.join(context.args)
    if not query:
        await update.message.reply_text("Por favor, forneça uma palavra-chave. Exemplo: /search bruh")
        return

    results = search_myinstants(query)
    if not results:
        await update.message.reply_text(f"Nenhum som encontrado para '{query}'. Tente outra palavra.")
        return

    audio_name, audio_url = results[0]
    response = requests.get(audio_url)

    if response.status_code == 200:
        audio_path = f"{audio_name}.mp3"
        with open(audio_path, 'wb') as f:
            f.write(response.content)

        if os.path.getsize(audio_path) > 0:
            await update.message.reply_audio(audio=open(audio_path, 'rb'))
        else:
            await update.message.reply_text("Erro: O arquivo de áudio está vazio.")
        os.remove(audio_path)
    else:
        await update.message.reply_text("Erro ao baixar o áudio. Tente novamente mais tarde.")

async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query
    if not query:
        return

    results = search_myinstants(query)
    if not results:
        return

    inline_results = []
    for idx, (audio_name, audio_url) in enumerate(results[:10]):
        inline_results.append(
            InlineQueryResultAudio(
                id=str(idx),
                title=audio_name,
                audio_url=audio_url
            )
        )

    await update.inline_query.answer(inline_results)

# === MAIN ===
def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN não está definido nas variáveis de ambiente!")

    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("search", send_audio))
    application.add_handler(InlineQueryHandler(inline_query))

    # Thread para o web server
    Thread(target=run_web).start()

    # Loop de proteção para manter polling
    while True:
        try:
            print("Bot rodando...")
            application.run_polling()
        except Exception as e:
            print(f"Erro no bot: {e}")
            time.sleep(5)

if __name__ == '__main__':
    main()
