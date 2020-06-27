# DiscordBot

first setup:


sudo apt-get install libzbar-dev

pip install zbar-py

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
accounts and such: 
<ul>
	<li>TWITCH API KEY</li>
	<li>TWITCH API SECRET</li>
		<ul><li>https://dev.twitch.tv/console/apps</li></ul>
	<li>YOUR TWITCH BOT NAME</li>
		<ul><li>normal twitch account</li></ul>
	<li>YOUR TWITCH BOT OAUTH TOKEN</li>
		<ul><li>https://twitchapps.com/tmi/</li></ul>
 	<li>YOUTUBE API KEY</li>
 		<ul><li>https://console.developers.google.com/?pli=1</li></ul>
 	<li>YOUR DISCORD API KEY</li>
 		<ul><li>https://discord.com/developers</li></ul>
 	<li>YOUR EMAIL ADDRESS</li>
 		<ul><li>example@gmail.com</li></ul>
 	<li>YOUR EMAIL APPPLICATION PASSWORD</li>
 		<ul><li>https://myaccount.google.com/apppasswords</li></ul>
 </ul>	
 
 
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
