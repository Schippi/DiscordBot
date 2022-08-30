'''
Created on 16 Jun 2021

@author: Carsten Schipmann
'''
import traceback
import sys

def update(db, open_db_connection):
    open_db_connection.execute('''CREATE TABLE IF NOT EXISTS twitchstats (
    'ID'    INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    'DATE'    TEXT,
    'viewcount'    INTEGER,
    'game'    TEXT,
    'channel'    TEXT
);''');

    open_db_connection.execute('''CREATE TABLE IF NOT EXISTS  `control` (
            `Key`    TEXT UNIQUE,
            `value`    TEXT
        );''');
    
    open_db_connection.execute('''CREATE TABLE IF NOT EXISTS  `game` (
            `id`    INTEGER UNIQUE,
            `name`    TEXT,
            `boxart`    TEXT
        );''');
    
    open_db_connection.execute('''CREATE TABLE IF NOT EXISTS  `twitch_person` (
            `id`    TEXT UNIQUE,
            `login`    TEXT,
            `display_name`    TEXT,
            `type`    TEXT,
            `broadcaster_type`    TEXT,
            `description`    TEXT,
            `profile_image_url`    TEXT,
            `offline_image_url`    TEXT,
            `view_count`    INTEGER,
            `last_check`    TEXT,
            `last_check_status`    TEXT
        );''');
        
        
        
    
    try:
        open_db_connection.execute("select sql from sqlite_master where type='table' and name='twitch_sub'")
        schema = open_db_connection.fetchone();
        if ("unique" in schema['sql'].lower()):
            open_db_connection.execute('''DROP TABLE `twitch_sub`''');
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        pass;
        
    open_db_connection.execute('''CREATE TABLE IF NOT EXISTS  `twitch_sub` (
            `broadcaster_id`    TEXT,
            `broadcaster_name`    TEXT,
            `gifter_id`    TEXT,
            `gifter_name`    TEXT,
            `is_gift`    TEXT,
            `plan_name`    TEXT,
            `tier`    TEXT,
            `user_id`    TEXT,
            `user_name`    INTEGER
        );''');
    
    open_db_connection.execute('''CREATE TABLE IF NOT EXISTS  `dual` (
            `DUMMY`    TEXT
        );''');
        
    open_db_connection.execute('''insert into dual(dummy)
                        select 'X' from sqlite_master 
                        where not exists (select * from dual)
                        limit 1''');
        
    open_db_connection.execute('''CREATE TABLE IF NOT EXISTS  `irc_channel` (
            `channel`    TEXT,
            `joined`    TEXT,
            `left`    TEXT
        );''');
    
        
    for row in open_db_connection.execute('''select * from dual inner join irc_channel on 1 = 1 limit 1'''):
        if('raid_auto' in row.keys()):
            pass;
        else:
            open_db_connection.execute('''alter table irc_channel add raid_auto integer''');
            open_db_connection.execute('''update irc_channel set raid_auto = 0''');
        if('raid_time' in row.keys()):
            pass;
        else:
            open_db_connection.execute('''alter table irc_channel add raid_time integer''');
            open_db_connection.execute('''update irc_channel set raid_time = 10''');  
    
    for row in open_db_connection.execute('''select * from twitch limit 1'''):
        if('last_msg_id' in row.keys()):
            pass;
        else:
            open_db_connection.execute('''alter table twitch add last_msg_id text''');
        if('embedtitle' in row.keys()):
            pass;
        else:
            open_db_connection.execute('''alter table twitch add embedtitle text''');
            
    for row in open_db_connection.execute('''select * from twitch_person limit 1'''):
        if('subs' in row.keys()):
            pass;
        else:
            open_db_connection.execute('''alter table twitch_person add subs integer''');
        if('subs_auth_token' in row.keys()):
            pass;
        else:
            open_db_connection.execute('''alter table twitch_person add subs_auth_token text''');
        if('refresh_token' in row.keys()):
            pass;
        else:
            open_db_connection.execute('''alter table twitch_person add refresh_token text''');
        if('watching_raid_id' in row.keys()):
            pass;
        else:
            open_db_connection.execute('''alter table twitch_person add watching_raid_id text''');
        if('watching_raid_id_from' in row.keys()):
            pass;
        else:
            open_db_connection.execute('''alter table twitch_person add watching_raid_id_from text''');
        if('watching_since' in row.keys()):
            pass;
        else:
            open_db_connection.execute('''alter table twitch_person add watching_since text''');
    
    open_db_connection.execute('''CREATE TABLE IF NOT EXISTS  `urlmap` (
            'ID'    INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            `short`    TEXT UNIQUE,
            `long`    TEXT
        );''');
    for row in open_db_connection.execute('''select * from urlmap limit 1'''):
        if('used' in row.keys()):
            pass;
        else:
            open_db_connection.execute('''alter table urlmap add used INTEGER DEFAULT 0''');
    
    db.commit();
            
    open_db_connection.execute('''CREATE TABLE IF NOT EXISTS  `token` (
            `id`    INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            `token`    TEXT,
            `display_name`    TEXT UNIQUE
        );''');
        
    #open_db_connection.execute('''drop TABLE `connection`''')
        
    open_db_connection.execute('''CREATE TABLE IF NOT EXISTS  `connection` (
        `date`    TEXT,
        `from_channel`    TEXT,
        `to_channel`    TEXT,
        `kind`    TEXT,
        `viewers`    INTEGER
    );''');
    
    for row in open_db_connection.execute('''select * from `connection` limit 1'''):
        if('from_game' in row.keys()):
            pass;
        else:
            open_db_connection.execute('''alter table `connection` add from_game text''');
        if('to_game' in row.keys()):
            pass;
        else:
            open_db_connection.execute('''alter table `connection` add to_game text''');
    
    for row in open_db_connection.execute('''select * from irc_channel limit 1'''):
        if('ghost' in row.keys()):
            pass;
        else:
            open_db_connection.execute('''alter table irc_channel add ghost text''');

    open_db_connection.execute('''CREATE TABLE IF NOT EXISTS  `bs_song` (
        `id`    TEXT,
        `hash`    TEXT,
        `name`    TEXT,
        `sub_name`    TEXT,
        `author`    TEXT,
        `mapper`    TEXT,
        `mapper_id`    TEXT,
        `cover_image` TEXT,
        `duration` INTEGER,
        `uploadtime` INTEGER
    );''')

    open_db_connection.execute('''CREATE TABLE IF NOT EXISTS  `bs_song_diff` (
        `id`    TEXT,
        `id_song`    TEXT,
        `difficultyName`    TEXT,
        `stars`    TEXT,
        `notes`    TEXT,
        `bombs`    TEXT,
        `walls` TEXT,
        `rankedTime` INTEGER,
        `nps` TEXT
    );''');

    open_db_connection.execute('''CREATE TABLE IF NOT EXISTS  `bs_replay` (
        `id`    TEXT,
        `id_diff`    TEXT,
        `id_user`    TEXT,
        `badCuts`    INTEGER,
        `missedNotes`    INTEGER,
        `bombCuts`    INTEGER,
        `wallsHit` INTEGER,
        `pauses` INTEGER,
        `fullCombo` INTEGER,
        `replay` TEXT,
        `modifiers` TEXT,
        `score` INTEGER
    );''');

    open_db_connection.execute('''CREATE TABLE IF NOT EXISTS  `bs_user` (
        `id_user`    TEXT,
        `user_name` TEXT
    );''');

    for row in open_db_connection.execute('''select * from `bs_replay` limit 1'''):
        if('timeset' in row.keys()):
            pass;
        else:
            open_db_connection.execute('''alter table `bs_replay` add timeset integer''');




    db.commit()