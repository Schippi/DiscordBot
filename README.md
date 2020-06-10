# DiscordBot

first setup:

install with pip

async_timeout==3.0.1

pip install yagmail

pip install aiohttp

pip install pytz

pip install discord.py

pip install pyzbar

pip install discord

pip install Pillow

pip install aiodns

pip install cchardet

pip install py-dateutil

pip install aiohttp_session

pip install cryptography

pip install twitchio
 
change twitchio.websocket.py:
	in join action:
	 edit the if clause:
	 	if self._pending_joins and channel in self._pending_joins.keys():
 
 
---------------------
mv cfg/empty.db cfg/bot.db

echo "YOUR TWITCH API KEY" > tokens/twitch.token

echo "YOUR TWITCH API SECRET" >> tokens/twitch.token

echo "YOUR TWITCH BOT NAME" > tokens/irc.token

echo "YOUR TWITCH BOT OAUTH TOKEN" >> tokens/irc.token

echo "YOUR YOUTUBE API KEY" > tokens/youtube.token

echo "YOUR DISCORD API KEY" > tokens/dicord.token

echo "YOUR EMAIL ADDRESS" > tokens/mail.token

echo "YOUR EMAIL APPPLICATION PASSWORD" >> tokens/mail.token


https://certbot.eff.org/
or
openssl req -x509 -sha256 -nodes -days 365 -newkey rsa:2048 -keyout cfg/privkey.pem -out cfg/fullchain.pem

cd src

python3 -u DiscordBot.py ../tokens/dicord.token ../cfg example.com 8080
