'''
Created on 18 May 2020

@author: Carsten Schipmann
'''


class TwitchStream:
    def __init__(self,dic):
        self.id = dic['id'];  
        self.game_id = dic['game_id']; 
        self.language = dic['language'];
        self.started_at = dic['started_at'];
        self.tag_ids = dic['tag_ids'];
        self.thumbnail_url = dic['thumbnail_url'].replace('{width}',str(16*20)).replace('[height}',str(9*20));
        self.title = dic['title'];
        self.type = dic['type'];
        self.user_id = dic['user_id'];
        self.user_name = dic['user_name'];
        self.viewer_count = dic['viewer_count'];
        self.url = 'https://twitch.tv/'+self.user_name;
    def isRerun(self):
        return self.type.lower() == 'rerun';

class TwitchGame:
    def __init__(self,dic):
        self.id = dic['id'];
        self.name = dic['name']; 
        self.box_art_url = dic['box_art_url'];

class TwitchUser:
    def __init__(self,dic):
        self.id = dic['id']; 
        self.login = dic['login'];
        self.display_name = dic['display_name'];
        self.type = dic['type'];
        self.broadcaster_type = dic['broadcaster_type'];
        self.description = dic['description'];
        self.profile_image_url = dic['profile_image_url'];
        self.offline_image_url = dic['offline_image_url'];
        self.view_count = dic['view_count'];
        if('email' in dic.keys()):
            self.email = dic['email'];
        else:
            self.email = '';
            
        #local stuff    
        if('last_check' in dic.keys()):
            self.last_check = dic['last_check'];
        else:
            self.last_check = '';
        if('last_check_status' in dic.keys()):
            self.last_check_status = dic['last_check_status'];
        else:
            self.last_check_status = '';