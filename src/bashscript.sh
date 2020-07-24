#!/bin/bash
#pip3 install pip --upgrade
#pip3 list --outdated --format=freeze | grep -v '^\-e' | cut -d = -f 1  | xargs -n1 pip install -U
git pull
COUNTER=0
while [ $COUNTER  -le 10 ]; do
	python3 -u DiscordBot.py ../tokens/live.token ../cfg theschippi.dynv6.net 443 |& tee -i -a ~/Discordbot.log
	echo bash script loop $COUNTER
	sleep 6m
	let COUNTER=COUNTER+1
done
python3 ErrorMail.py $COUNTER
while [ $COUNTER  -le 20 ]; do
	python3 -u DiscordBot.py ../tokens/live.token ../cfg theschippi.dynv6.net 443 |& tee -i -a ~/Discordbot.log
	echo bash script loop $COUNTER
	sleep 6m
	let COUNTER=COUNTER+1
done
python3 ErrorMail.py $COUNTER
