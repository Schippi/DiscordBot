settings = {};
adminId = 106087197588889600;
adminIds = [106087197588889600];

cfgPath = "cfg"
#Discordbot/src/cfg/
#cfg/

def getSetting(idd = None, context = None):
	if idd:
		if(idd in settings.keys()):
			#print(settings[id])
			return settings[idd];
	else:
		if(context.message.guild.id in settings.keys()):
			#print(settings[context.message.guild.id])
			return settings[context.message.guild.id];
	return None;

import datetime;
import entities.Permission;
import entities.CommandDef;
from util import updateOrInsert;
import util;

class Timeout:
	usr = None;
	until = None;
	oldRoles = [];

class GuildSetting:
	id = 0;
	welcomeMessage = '';
	scheduleMessage = '';
	logLevel = 'channel';
	prefix = '!';
	commandpermissions = [];
	timeouts = {};
	customCommands = [];
	guild = '';
	
	def __str__(self):
		return str(self.id+'\n\t '+str(self.commandpermissions)+'\n\t '+self.scheduleMessage+'\n\t '+self.welcomeMessage+'\n\t '+self.logLevel+'\n\t '+self.prefix);
						
	def __init__(self,guild):
		self.id = guild.id;
		self.guild = guild;
		settings[guild.id] = self;
		self.loadSettings();
	
	def setWelcomeMessage(self,msg):
		self.welcomeMessage = msg;
		self.saveSettings();
	
	def getWelcomeMessage(self):
		return self.welcomeMessage;
	
	def setLogLevel(self,msg):
		self.logLevel = msg;
		self.saveSettings();
	
	def getLogLevel(self):
		return self.logLevel;
	
	def addPermission(self,roleID,command, gosave = True):
		if not self.hasPermission(roleID,command):
			p = entities.Permission.CommandPermission(None, self.id, command, roleID);
			self.commandpermissions.append(p);
			p.save();
				
	def removePermission(self,roleID,command):
		for perm in self.commandpermissions:
			if perm.command == command and perm.role == roleID:
				self.commandpermissions.remove(perm);
				perm.remove();
				return;
				
	def hasPermission(self,roleID,command):
		askingRole = None;
		for r in self.guild.roles:
			if r.id == roleID:
				askingRole = r;
		if askingRole:		
			for perm in self.commandpermissions:
				if perm.command.lower() == command.lower():
					checkingRole = None;
					for r in self.guild.roles:
						if r.id == perm.role:
							checkingRole = r;
					if checkingRole:
						print(askingRole.name + ' asks ' + checkingRole.name)
						if askingRole >= checkingRole:
							print('c' + checkingRole.name)
							return True;
		return False;
	
	def addCom(self,cmd,response):
		for c in self.customCommands:
			if c.command == cmd:
				return False;
		c = entities.CommandDef.Command(None,self.id,cmd,response);
		self.customCommands.append(c);
		self.addPermission('@everyone',cmd);
		c.save();
		return True;
		
	def editCom(self,cmd,response):
		for c in self.customCommands:
			if c.command == cmd:
				c.response = response;
				c.save();
				return True;
		return False;
	
	def setCom(self,cmd,response):
		if not self.addCom(cmd,response):
			self.editCom(cmd,response);
			
	def delCom(self,cmd):
		for c in self.customCommands:
			if c.command == cmd:
				c.delete();
				self.customCommands.remove(c);
				return True;
		return False;
		
	def timeoutPerson(self, usr, amount):
		for mem in self.guild.members:
			if ((mem.name+'#'+mem.discriminator == usr) or (str(mem.id) == usr)) and (mem.id != adminId):
				print('timed out'+'   '+mem.name+'#'+mem.discriminator)
				until = datetime.datetime.utcnow() + datetime.timedelta(seconds = amount);
				timout = Timeout();
				timout.until = amount;
				timout.usr = mem;
				for role in mem.roles:
					timout.oldRoles.append(role);
				self.timeouts[mem.id] = until;	
				self.saveSettings();
				return True;
		return False;
			
		
			
	def saveSettings(self):
		qdkp = {'id':self.id};
		qd = {'welcome':self.welcomeMessage,
			'schedule': self.scheduleMessage,
			'loglevel': self.logLevel,
			'prefix': self.prefix};
		updateOrInsert('guild', qdkp, qd,True);
		
		for k in self.customCommands:
			k.save(False);
		
		for k in self.commandpermissions:
			k.save(False);
			
		util.DB.commit();
	
	def loadSettings(self):
		t = (self.id,);
		util.DBcursor.execute('SELECT * FROM guild where id = ?',t);
		row1 = util.DBcursor.fetchone();
		if row1:
			self.welcomeMessage = row1['welcome'] if row1['welcome'] else '';
			self.scheduleMessage = row1['schedule'] if row1['schedule'] else '';
			self.logLevel = row1['loglevel'] if row1['loglevel'] else 'channel';
			self.prefix = row1['prefix'] if row1['prefix'] else '!';
			self.commandpermissions = entities.Permission.load(self.id);
			self.customCommands = entities.CommandDef.load(self.id);
			
	def threadwait(self,timout):
		pass;
		#sleep(timout.until);
		
	def isAllowed(self,userID, command):
		membr = self.guild.get_member(userID);
		if not membr:
			return False
		allow = (userID in adminIds) or (membr == self.guild.owner);
		print(allow);
		print(userID);
		print(adminIds);
		if membr.roles:
			for role in membr.roles:
				#mit und ohne !
				allow = allow or self.hasPermission(role.id,command) or self.hasPermission(role.id,command[1:]);
		allow = allow and not membr.bot;
		return allow;
	
def isAllowed(contxt = None, userid = None, guildid = None, command = None):
	if isAdmin(contxt) or userid in adminIds:
		return True;
	if not contxt or not contxt.message or not contxt.message.guild:
		if guildid:
			sett = getSetting(idd = guildid);
			cmd = command;
		else :
			return False;
	else:
		cmd = contxt.message.content.split(" ",1)[0];
		return isAllowed(None,contxt.message.author.id,contxt.message.guild.id,cmd);
	try:	
		return sett.isAllowed(userID = userid, command = cmd);
	except:
		return False;
		
def isAdmin(contxt):	
	if not contxt or not contxt.message:
		return False;			
	return contxt.message.author.id in adminIds;	


				
				
				
				
				
				
				
				
				