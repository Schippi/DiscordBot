import datetime
import util;
from util import updateOrInsert;
import discord;
import time;

defaultTimerText = '@here```im here to remind you of this super cool thing```';

#wget -O- "https://www.googleapis.com/youtube/v3/channels?part=contentDetails&key=AIzaSyDr5ehqH9ODFOGJSK26Ef1zwEtIQQhvMYs&forUsername=hybridpanda"
#wget -O- "https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&key=AIzaSyDr5ehqH9ODFOGJSK26Ef1zwEtIQQhvMYs&playlistId=UUkcdIHabg9Sq0sD6ITyVQcg"


def repl(inp,toreplace,replacewith):
	if(replacewith):
		return inp.replace(toreplace,replacewith);
	else:
		return inp;

class TimerEntry:
	
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
		if dic['executed']:
			self.executed = dic['executed'].lower().strip();
		else:
			self.executed = None;
		if dic['embedmessage']:
			self.embedmessage = dic['embedmessage'];
		else:
			self.embedmessage = None;
		if not self.text:
			self.text = defaultTimerText;
		self.description = dic['description'];			
		try:
			self.fromtimeH = int(dic['fromh']);
			self.fromtimeM = int(dic['fromm']);
			self.days = [int(i) for i in dic['days'].split(',')];
		except:
			self.fromtimeH = None;
			self.fromtimeM = None;
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
			'days':", ".join(dd),
			'color':self.color,
			'embedmessage':self.embedmessage,
			'executed':self.executed,
			'avatar':self.avatar
			};
		self.id = updateOrInsert('timer',{'id':self.id},dic,False);
		util.DB.commit();
		
	def getYString(self,start,name,url,title, image):
		ret = start;
		ret = repl(ret,'%%name%%',name);
		ret = repl(ret,'%%url%%',url);
		ret = repl(ret,'%%title%%',title);
		ret = repl(ret,'%%img%%',image);
		ret = repl(ret,'%%time%%',time.strftime('%X'));
		return ret;
		
	def getEmbed(self,name,url,title, image):
		embed = None;
		if self.embedmessage and self.color:
			ret = self.getYString(self.embedmessage,name,url,title, image);
			embed = discord.Embed(colour=discord.Colour(self.color), 
								url=url, 
								description=ret);
			if self.avatar:					
				embed.set_thumbnail(url=self.avatar);
		return embed;	
		
	def getJSONdict(self,name,url = None,logo = None,title = None,image = None):
		#return d;
		d = {'content':self.getYString(name,url,title,image),
			'description':self.description}
		if(not self.avatar is None):
			d['avatar_url'] = self.avatar;
		elif((not logo is None) and (len(logo) > 0)):
			d['avatar_url'] = logo;	
		return d;	
	
	def __str__(self):
		s = 'timer: id:'+self.id;
		return s;
		
	def shouldprint(self : str):
		if self.fromtimeH is None or self.fromtimeM is None:
			return False;
		now = datetime.datetime.now();
		if self.executed:
			try:
				nexxt = self.executed.split('-');
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
			self.executed = nextdate.strftime("%d-%m-%Y");
			self.save();
			return now.weekday() in self.days;			
		return False;
		
				
				
				
				
				
				
				
				
				
				
				
				
				
				
				
				
				