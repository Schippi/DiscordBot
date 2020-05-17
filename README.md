# DiscordBot

first setup:

install with pip

yagmail==0.11.220

async_timeout==3.0.1

aiohttp==3.5.4

pytz==2019.1

discord.py==1.2.5

pyzbar==0.1.8

discord==1.0.1

Pillow==7.0.0

pip install aiodns

pip install cchardet

---------------------
mv cfg/empty.db cfg/bot.db

echo "YOUR TWITCH API KEY" > tokens/twitch.token

echo "YOUR YOUTUBE API KEY" > tokens/youtube.token

echo "YOUR DISCORD API KEY" > tokens/dicord.token

echo "YOUR EMAIL ADDRESS" > tokens/mail.token

echo "YOUR EMAIL APPPLICATION PASSWORD" >> tokens/mail.token

cd src

python3 -u DiscordBot.py ../tokens/dicord.token ../cfg
