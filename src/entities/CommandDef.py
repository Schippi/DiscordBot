'''
Created on 02.09.2017

@author: Carsten Schipmann
'''

from util import updateOrInsert;
import util;

class Command:
    id = None;
    command = '';
    serverid = None;
    response = None;
    
    def __init__(self,idd,serverid,command,response):
        self.id = idd;
        self.command = command;
        self.response = response;
        self.serverid = serverid;
    
    def __str__(self):
        return str(self.id)+' - '+self.command;
        
        
    def save(self, commit = True):
        qdkp = {'id':self.id};
        qd = {'ID_Server':self.serverid,
            'command': self.command,
            'response': self.response};
        self.id = updateOrInsert('commands', qdkp, qd,False);
        if commit:
            util.DB.commit();
            
    def delete(self):
        util.delete('commands', 'id', self.id);
        util.DB.commit();
        
def load(serverid):
    result = [];
    t = (serverid,);
    for row in util.DBcursor.execute('SELECT * FROM commands where ID_Server = ?',t):
        result.append(Command(row['id'],row['id_server'],row['command'],row['response']));
    return result;
    
        
    