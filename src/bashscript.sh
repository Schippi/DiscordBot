#!/bin/bash
COUNTER=0
while [ $COUNTER  -le 10 ]; do
	python3 -u DiscordBot.py tokens/live.token cfg |& tee -i -a ~/Discordbot.log
	echo bash script loop $COUNTER
	sleep 6m
	let COUNTER=COUNTER+1
done
python3 ErrorMail.py $COUNTER
while [ $COUNTER  -le 20 ]; do
	python3 -u DiscordBot.py tokens/live.token cfg |& tee -i -a ~/Discordbot.log
	echo bash script loop $COUNTER
	sleep 6m
	let COUNTER=COUNTER+1
done
python3 ErrorMail.py $COUNTER
