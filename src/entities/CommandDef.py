'''
Created on 02.09.2017

@author: Carsten Schipmann
'''

from util import updateOrInsert;
import util;

class Command:
    id = None;
    command = '';
    guildid = None;
    response = None;
    
    def __init__(self,idd,guildid,command,response):
        self.id = idd;
        self.command = command;
        self.response = response;
        self.guildid = guildid;
    
    def __str__(self):
        return str(self.id)+' - '+self.command;
        
        
    def save(self, commit = True):
        qdkp = {'id':self.id};
        qd = {'ID_Guild':self.guildid,
            'command': self.command,
            'response': self.response};
        self.id = updateOrInsert('commands', qdkp, qd,False);
        if commit:
            util.DB.commit();
            
    def delete(self):
        util.delete('commands', 'id', self.id);
        util.DB.commit();
        
def load(guildid):
    result = [];
    t = (guildid,);
    for row in util.DBcursor.execute('SELECT * FROM commands where ID_Guild = ?',t):
        result.append(Command(row['id'],row['id_guild'],row['command'],row['response']));
    return result;
    
        
    