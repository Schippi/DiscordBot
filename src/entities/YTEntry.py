import datetime
import util;
from util import updateOrInsert;
import discord;
import time;

defaultYTText =     '@here```diff\n- %%name%% just released a new video!\n%%title%%```%%url%%';
defaultStreamUser = 'Stream Alert';
defaultYTUser = 'Video Alert';

#wget -O- "https://www.googleapis.com/youtube/v3/channels?part=contentDetails&key=AIzaSyDr5ehqH9ODFOGJSK26Ef1zwEtIQQhvMYs&forUsername=hybridpanda"
#wget -O- "https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&key=AIzaSyDr5ehqH9ODFOGJSK26Ef1zwEtIQQhvMYs&playlistId=UUkcdIHabg9Sq0sD6ITyVQcg"


def repl(inp,toreplace,replacewith):
	if(replacewith):
		return inp.replace(toreplace,replacewith);
	else:
		return inp;

class YTEntry:
	
	def __init__(self,dic):
		self.id = dic['id']; 
		self.guild = int(dic['id_guild']);
		self.channel = int(dic['id_channel']);
		self.text = dic['message'];
		self.image = dic['image'];
		self.wasprinted = dic['wasprinted'];
			
		if ('lastprinted' in dic) and dic['lastprinted']:
			self.lastPrinted = util.toDateTime(dic['lastprinted']);
		else:
			self.lastPrinted = None;
		if dic['color']:
			self.color = dic['color'];
		else:
			self.color = 0x4c0544; 
		self.embedmessage = None;
		if not self.text:
			self.text = defaultYTText;
		self.username = dic['username'];			
		
	def save(self):
		dic = {'id_guild':self.guild,
			'id_channel': self.channel,
			'message': self.text,
			'username': self.username,
			'color':self.color,
			'embedmessage':self.embedmessage,
			'image':self.image,
			'wasprinted':self.wasprinted
			};
		self.id = updateOrInsert('youtube',{'id':self.id},dic,False);
		util.DB.commit();
				
	def getYString(self,start,name,url,title, image):
		ret = start;
		ret = repl(ret,'%%name%%',name);
		ret = repl(ret,'%%url%%',url);
		ret = repl(ret,'%%title%%',title);
		ret = repl(ret,'%%thumbnail%%',image);
		ret = repl(ret,'%%time%%',time.strftime('%X'));
		return ret;
		
	def getEmbed(self,name,url,title, image):
		embed = None;
		if self.embedmessage and self.color:
			ret = self.getYString(self.embedmessage,name,url,title, image);
			embed = discord.Embed(colour=discord.Colour(self.color), 
								url=url, 
								description=ret);
			if self.image:					
				embed.set_thumbnail(url=self.image);
		return embed;	
	
	def __str__(self):
		s = 'Hook: '+self.link+'\n'+'username: '+self.username+'\n'+'text: '+self.text;
		if self.image:
			s = s+'\nimage: '+self.image;
		return s;
		
	def shouldprint(self, time : datetime.datetime):
		if (not self.wasprinted) or (not self.lastPrinted):
			self.wasprinted = 1;
			self.save();
			return False;
		else:
			if time > self.lastPrinted:
				return True;
			return False;
			
				
				
				
				
				
				
				
				
				
				
				
				
				
				
				
				
				