import datetime
import util;
from util import updateOrInsert;
import discord;
import time;

defaultStreamText = '@here```diff\n+ %%name%% just went live playing %%game%%!\n%%title%%```%%url%%';
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

class TwitchEntry:
	
	def __init__(self,dic):
		self.id = dic['id']; 
		self.guild = int(dic['id_guild']);
		self.channel = int(dic['id_channel']);
		self.avatar = None;
		self.text = dic['message'];
		self.avatar = dic['avatar'];
		if dic['color']:
			self.color = dic['color'];
		else:
			self.color = 0x4c0544; 
		if dic['game']:
			self.game = dic['game'].lower().strip();
		else:
			self.game = None;
		if dic['last_check_status']:
			self.last_check_status = dic['last_check_status'];
		else:
			self.last_check_status = None;
		if dic['last_check']:
			self.last_check_status = dic['last_check'];
		else:
			self.last_check_status = None;
		if dic['embedmessage']:
			self.embedmessage = dic['embedmessage'];
		else:
			self.embedmessage = None;
		if not self.text:
			self.text = defaultStreamText;
		self.username = dic['username'];			
		try:
			self.fromtimeH = int(dic['fromh']);
			self.fromtimeM = int(dic['fromm']);
			self.untiltimeH = int(dic['untilh']);
			self.untiltimeM = int(dic['untilm']);
			self.days = [int(i) for i in dic['days'].split(',')];
		except:
			self.fromtimeH = None;
			self.fromtimeM = None;
			self.untiltimeH = None;
			self.untiltimeM = None;
			self.days = [];	
			pass;
		self.enableYT(False);
	
	def save(self):
		dd = [str(i) for i in self.days];
		dic = {'id_guild':self.guild,
			'id_channel': self.channel,
			'message': self.text,
			'username': self.username,
			'fromh':self.fromtimeH,
			'fromm':self.fromtimeM,
			'untilh':self.untiltimeH,
			'untilm':self.untiltimeM,
			'days':", ".join(dd),
			'color':self.color,
			'embedmessage':self.embedmessage,
			'game':self.game,
			'avatar':self.avatar
			};
		self.id = updateOrInsert('twitch',{'id':self.id},dic,False);
		util.DB.commit();
		
	def enableYT(self,val):
		self.YT = val;
		if(val):
			if(self.username == defaultStreamUser):
				self.username = defaultYTUser;
			if(self.text == defaultStreamText):
				self.text = defaultYTText;
				
	def getYString(self,start,name,game,url,title, image):
		ret = start;
		ret = repl(ret,'%%name%%',name);
		ret = repl(ret,'%%game%%',game);
		ret = repl(ret,'%%url%%',url);
		ret = repl(ret,'%%title%%',title);
		ret = repl(ret,'%%img%%',image);
		ret = repl(ret,'%%time%%',time.strftime('%X'));
		return ret;
		
	def getEmbed(self,name,game,url,title, image):
		embed = None;
		if self.embedmessage and self.color:
			ret = self.getYString(self.embedmessage,name,game,url,title, image);
			embed = discord.Embed(colour=discord.Colour(self.color), 
								url=url, 
								description=ret);
			if self.avatar:					
				embed.set_thumbnail(url=self.avatar);
		return embed;	
		
	def getJSONdict(self,name,game = None,url = None,logo = None,title = None,image = None):
		#return d;
		d = {'content':self.getYString(name,game,url,title,image),
			'username':self.username}
		if(not self.avatar is None):
			d['avatar_url'] = self.avatar;
		elif((not logo is None) and (len(logo) > 0)):
			d['avatar_url'] = logo;	
		return d;	
	
	def __str__(self):
		s = 'Hook: '+self.link+'\n'+'username: '+self.username+'\n'+'text: '+self.text;
		if self.avatar:
			s = s+'\navatar: '+self.avatar;
		return s;
		
	def shouldprint(self, game : str):
		if self.username == 'timer':
			if self.fromtimeH is None or self.fromtimeM is None:
				return False;
			now = datetime.datetime.now();
			if self.game:
				try:
					nexxt = self.game.split('-');
					if(len(nexxt) != 3):
						return False;
					ty = int(nexxt[2]);
					tm = int(nexxt[1]);
					td = int(nexxt[0]);
				except: 
					ty = int(now.year);
					tm = int(now.month);
					td = int(now.day);	
			else:
				ty = int(now.year);
				tm = int(now.month);
				td = int(now.day);
			fromdate = datetime.datetime(ty,tm,td,int(self.fromtimeH),int(self.fromtimeM));
			if(now > fromdate):
				nextdate = datetime.datetime(now.year,now.month,now.day);
				while True:
					nextdate = nextdate + datetime.timedelta(days=1);
					if nextdate.weekday() in self.days:
						break;
				self.game = nextdate.strftime("%d-%m-%Y");
				self.save();
				return now.weekday() in self.days;			
			return False;
		if self.game and (self.game != game.lower().strip()):
			return False;
		if ((not self.days) or 
			(len(self.days) == 0) or 
			(self.fromtimeH is None) or 
			(self.untiltimeH is None) or 
			(self.fromtimeM is None) or 
			(self.untiltimeM is None)):
			return True;
		else:
			now = datetime.datetime.now();
			if now.weekday() in self.days: 
				fromdate = datetime.time(int(self.fromtimeH),int(self.fromtimeM));
				todate = datetime.time(int(self.untiltimeH),int(self.untiltimeM));
				nowdate = datetime.time(now.hour,now.minute);
				if(fromdate < todate):
					return (nowdate > fromdate) and (nowdate < todate)
				else:
					return (nowdate < fromdate) and (nowdate > todate)							
			else:
				return False;
				
				
				
				
				
				
				
				
				
				
				
				
				
				
				
				
				