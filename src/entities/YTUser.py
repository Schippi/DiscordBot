
import util;
from util import updateOrInsert;

class YTUser:
    
    def __init__(self,dic):
        self.id = dic['idytid'];
        self.username = dic['username'];
        self.YTID = dic['ytid'];
        self.lastprinted = dic['lastprinted'];
        self.uploadID = dic['uploadid'];
        if 'displayname' in dic:
            self.displayname = dic['displayname'];
        else:
            self.displayname = None;
        self.lastID = dic['lastid'];
        self.changed = False;
        
    def save(self):
        dic = {'ytid':self.YTID,
            'lastprinted': self.lastprinted,
            'uploadid': self.uploadID,
            'lastid':self.lastID,
            'username':self.username,
            'displayname':self.displayname
            };
        self.id = updateOrInsert('YTUser',{'id':self.id},dic,False);
        util.DB.commit();