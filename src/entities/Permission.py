'''
Created on 02.09.2017

@author: Carsten Schipmann
'''
from util import updateOrInsert;
import util;


class CommandPermission:
    
    guildid = None;
    command = None;
    role = None;
    id = None;
            
    def __init__(self,idd, guildid,command,role):
        self.id = idd;
        self.guildid = guildid;
        self.command = command;
        self.role = str(role);
        
    def __str__(self):
        return str(self.id)+' - '+self.command+' - '+self.role;
        
    def save(self, commit = True):
        qdkp = {'id':self.id};
        qd = {'ID_Guild':self.guildid,
            'command': self.command,
            'ID_Role': self.role};
        self.id = updateOrInsert('permissions', qdkp, qd,False);
        if commit:
            util.DB.commit();
        
    def remove(self):
        util.delete('permissions', 'id', self.id);
        util.DB.commit();


def load(guildid):
    result = [];
    t = (guildid,);
    for row in util.DBcursor.execute('SELECT * FROM permissions where ID_Guild = ?',t):
        result.append(CommandPermission(row['id'],row['id_guild'],row['command'],row['id_role']));
    return result;

        