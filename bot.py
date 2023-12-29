import telebot 
import json 
import subprocess # для управления командной строкой
import pandas as pd
import re
from transformers import pipeline


model = pipeline(
    model="lxyuan/distilbert-base-multilingual-cased-sentiments-student", 
    top_k=None
)

print('Model has been loaded')


# инициализация
TOKEN = '<YOUR_TOKEN>'
bot = telebot.TeleBot(TOKEN)

tickers_df = pd.read_csv('data/tickers.csv') # 'Symbol', 'Name', 'Country', 'Sector', 'Industry'
moex_tickers_df = pd.read_csv('data/moex_tickers.csv') # 'Name', 'Symbol'

def collect_posts(channel):
    with open(f"data/{channel}.txt") as file:
        file = file.readlines()
    posts = []
    for n, line in enumerate(file):
        file[n] = json.loads(file[n])
        links = [link for link in file[n]['outlinks'] if channel not in link]
        p = str(file[n]['content']) + "\n\n" + str("\n".join(links))
        posts.append(p)
    return posts 


def upload_posts(num_posts, channel):
    command = f'snscrape --max-result {num_posts} --jsonl telegram-channel {channel} > data/{channel}.txt'
    subprocess.run(command, shell=True)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Write:\n1. Channel name (e.g. markettwits)\n2. How many recent posts to upload\n3. This channel ID\n\nExample:\nmarkettwits 10 MarketTwits_tonality_bot")     


@bot.message_handler(content_types=["text"])
def send_posts(message):
    try:
        channel, num_posts, target_channel = str(message.text).split()
        target_channel = "@"+target_channel
        
        upload_posts(num_posts, channel)
        posts = collect_posts(channel)
        for post in posts:
            tickers = re.findall(r"([#$][A-Z]+\b)", post)
            if len(tickers) > 0:
                ticker_temp = tickers[0][1:]
                sentiment_result = model(post)

                sent = (f"Sentiment prediction results:\n"
                        f"{sentiment_result[0][0]['label']}: {round(sentiment_result[0][0]['score'], 3)}\n"
                        f"{sentiment_result[0][1]['label']}: {round(sentiment_result[0][1]['score'], 3)}\n"
                        f"{sentiment_result[0][2]['label']}: {round(sentiment_result[0][2]['score'], 3)}\n\n\n")

                if ticker_temp in tickers_df['Symbol'].values:
                    ind = tickers_df[tickers_df['Symbol'] == ticker_temp].index[0]
                    desc = (f"#{tickers_df.loc[ind, 'Symbol']}\n"
                            f"Company name: {tickers_df.loc[ind, 'Name']}\n"
                            f"Country: {tickers_df.loc[ind, 'Country']}\n"
                            f"Sector: {tickers_df.loc[ind, 'Sector']}\n"
                            f"Industry: {tickers_df.loc[ind, 'Industry']}\n\n")
                    
                elif ticker_temp in moex_tickers_df['Symbol'].values:
                    ind = moex_tickers_df[moex_tickers_df['Symbol'] == ticker_temp].index[0]
                    desc = (f"#{moex_tickers_df.loc[ind, 'Symbol']}\n"
                            f"Company Name: {moex_tickers_df.loc[ind, 'Name']}\n\n")
                    
                else:
                    desc = f"#{ticker_temp}\n\n"

                bot.reply_to(message, desc+sent+post)

            else:
                continue

    except:
        bot.reply_to(message, "Wrong data format. Write /start and try again!")


if __name__ == "__main__":
    bot.polling()    