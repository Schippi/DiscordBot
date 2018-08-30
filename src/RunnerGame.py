'''
Created on 01.09.2017

@author: Carsten Schipmann
'''
import math;
import random;
from time import sleep;

async def printgrid(grid, playerpos, message,score, client):
    msg = ''
    for i in range(len(grid[0])):
        for j in range(len(grid)):
            if(j== 0 and playerpos == i):
                msg = msg +'x';
            else:
                msg = msg +grid[j][i];                
        msg = msg+'\n';
    await client.edit_message(message,'```\n'+msg+'\nscore: '+str(score)+'```');
    
def gameOver():
    return '+  ________\n+'+' /  _____/_____    _____   ____     _______  __ ___________ \n+'+'/   \\  ___\\__  \\  /     \\_/ __ \\   /  _ \\  \\/ // __ \\_  __ \\\n+'+'\\    \\_\\  \\/ __ \\|  Y Y  \\  ___/  (  <_> )   /\\  ___/|  | \\/\n+'+' \\______  (____  /__|_|  /\\___  >  \\____/ \\_/  \\___  >__|\n+'+'        \\/     \\/      \\/     \\/                   \\/';
    
async def playgame(message, playerID, client):
    playwidth = 10;
    playheight = 60;
    luecke = 5;
    playerpos = math.floor(playwidth /2);
    counter = 0;
    magicnumber = 50;
    membr = message.server.get_member(playerID);
    membrname = membr.nick if membr.nick else membr.name;
    
    playfield = [[0 for x in range(playwidth)] for y in range(playheight)] ;
    
    for i in range(len(playfield)):
        for j in range(len(playfield[0])):
            playfield[i][j] = ' ';
    
    score = 0;
    await printgrid(playfield,playerpos,message,0, client);
    
    for k in range(80):
        for i in range(playheight - 1):
            for j in range(playwidth):
                playfield[i][j] = playfield[i+1][j];
        if counter % (playwidth * 3) == (playwidth * 3) - 1:        
            luecke -= 1;
        if counter % playwidth == 0:
            smpl = random.sample(range(playwidth),playwidth-1);
            for j in range(playwidth):
                if j in smpl:
                    playfield[playheight - 1][j] = '#';
                else:
                    playfield[playheight - 1][j] = ' ';
                    missing = j;
                    
            for j in range(luecke):
                playfield[playheight - 1][(j+missing) % playwidth] = ' ';
        else:
            for j in range(playwidth):
                playfield[playheight - 1][j] = ' ';
                
        counter += 1;    
        
        if k > magicnumber:
            if playfield[0][playerpos] == '#':
                score -= 10;        
            await printgrid(playfield,playerpos,message,counter + score - magicnumber,client);
            sleep(0.7);
        
        if membr.voice.self_deaf or  membr.voice.deaf:
            playerpos = min(playerpos + 1,playwidth - 1);
        elif membr.voice.self_mute or membr.voice.mute:
            playerpos = max(playerpos - 1,0);
    
    score = counter + score - magicnumber;        
    await client.edit_message(message,'```diff\n'+gameOver()+'\n\n-        '+membrname+'\'s score: '+str(score)+'```');   
    