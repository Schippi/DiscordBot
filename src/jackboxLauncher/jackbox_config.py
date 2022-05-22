from dataclasses import dataclass


config = {
    'host': '::',
    'port': 8080
}


@dataclass
class PartyPack:
    name: str
    app_id: int


@dataclass
class GameItem:
    """Class for keeping track of an item in inventory."""
    name: str
    players_min: int = 1
    players_max: int = 0
    local_recommended: bool = False
    game: PartyPack = None
    drawing: bool = False
    image: str = None


PP1 = PartyPack(name='PartyPack01', app_id=331670)
PP2 = PartyPack(name='PartyPack02', app_id=397460)
PP3 = PartyPack(name='PartyPack03', app_id=434170)
PP4 = PartyPack(name='PartyPack04', app_id=610180)
PP5 = PartyPack(name='PartyPack05', app_id=774461)
PP6 = PartyPack(name='PartyPack06', app_id=774461)
PP7 = PartyPack(name='PartyPack07', app_id=1211630)
PP8 = PartyPack(name='PartyPack08', app_id=1552350)
PPStarter = PartyPack(name='StarterPack', app_id=1755580)
#PP9 = PartyPack(name='PartyPack9', app_id='app_id9')

games = [
    GameItem(name='You Don\'t Know Jack 2015', players_min=1, players_max=4, local_recommended=True, game=PP1, image='Jack_2015.webp'),
    GameItem(name='Drawful', players_min=3, players_max=8, local_recommended=False, drawing=True, game=PP1),
    GameItem(name='Word Spud', players_min=2, players_max=8, local_recommended=True, game=PP1),
    GameItem(name='Lie Swatter', players_min=1, players_max=100, local_recommended=False, game=PP1),
    GameItem(name='Fibbage XL', players_min=2, players_max=8, local_recommended=False, game=PP1),

    GameItem(name='Quiplash', players_min=2, players_max=10, local_recommended=False, game=PartyPack(name='Quiplash', app_id='351510')),

    GameItem(name='Fibbage 2', players_min=2, players_max=8, local_recommended=False, game=PP2),
    GameItem(name='Earwax', players_min=3, players_max=8, local_recommended=False, game=PP2),
    GameItem(name='Bidiots', players_min=3, players_max=6, local_recommended=False, drawing=True, game=PP2),
    GameItem(name='Quiplash XL', players_min=3, players_max=8, local_recommended=False, game=PP2),
    GameItem(name='Bomb Corp.', players_min=1, players_max=4, local_recommended=False, game=PP2),

    GameItem(name='Drawful 2', players_min=3, players_max=10, local_recommended=False, drawing=True, game=PartyPack(name='Drawful 2', app_id=442070)),
    GameItem(name='Fibbage XL', players_min=2, players_max=8, local_recommended=False, game=PartyPack(name='Fibbage XL', app_id=448080)), # this is the same as in PP1

    GameItem(name='Quiplash 2', players_min=3, players_max=8, local_recommended=False, game=PP3),
    GameItem(name='Trivia Murder Party', players_min=1, players_max=8, local_recommended=False, game=PP3),
    GameItem(name='Guesspionage', players_min=3, players_max=8, local_recommended=False, game=PP3),
    GameItem(name='Fakin\' It', players_min=3, players_max=6, local_recommended=True, game=PP3),
    GameItem(name='Tee K.O.', players_min=3, players_max=8, local_recommended=False, drawing=True, game=PP3),

    GameItem(name='Fibbage 3', players_min=2, players_max=8, local_recommended=False, game=PP4),
    GameItem(name='Survive the Internet', players_min=3, players_max=8, local_recommended=False, game=PP4),
    GameItem(name='Monster Seeking Monster', players_min=3, players_max=7, local_recommended=False, game=PP4),
    GameItem(name='Bracketeering', players_min=3, players_max=16, local_recommended=False, game=PP4),
    GameItem(name='Civic Doodle', players_min=3, players_max=8, local_recommended=False, drawing=True, game=PP4),

    GameItem(name='You Don\'t Know Jack Full Stream', players_min=1, players_max=8, local_recommended=False, game=PP5, image='Ydkjfullstream.webp'),
    GameItem(name='Split the Room', players_min=3, players_max=8, local_recommended=False, game=PP5),
    GameItem(name='Mad Verse City', players_min=3, players_max=8, local_recommended=False, game=PP5),
    GameItem(name='Zeeple Dome', players_min=1, players_max=6, local_recommended=True, game=PP5),
    GameItem(name='Patently Stupid', players_min=3, players_max=8, local_recommended=False, drawing=True, game=PP5),

    GameItem(name='Trivia Murder Party 2', players_min=1, players_max=8, local_recommended=False, game=PP6),
    GameItem(name='Role Models', players_min=3, players_max=6, local_recommended=False, game=PP6),
    GameItem(name='Joke Boat', players_min=3, players_max=8, local_recommended=False, game=PP6),
    GameItem(name='Dictionarium', players_min=3, players_max=8, local_recommended=False, game=PP6),
    GameItem(name='Push The Button', players_min=4, players_max=10, local_recommended=True, game=PP6),

    GameItem(name='Quiplash 2 InterLASHional', players_min=4, players_max=10, local_recommended=False, image='Quip2Translated.jpg', game=PartyPack(name='Quiplash 2 InterLASHional', app_id=1111940)),

    GameItem(name='Quiplash 3', players_min=3, players_max=8, local_recommended=False, game=PP7),
    GameItem(name='The Devils and the Details', players_min=3, players_max=8, local_recommended=True, game=PP7),
    GameItem(name='Champ\'d Up', players_min=3, players_max=8, local_recommended=False, drawing=True, game=PP7),
    GameItem(name='Talking Points', players_min=3, players_max=8, local_recommended=False, game=PP7),
    GameItem(name='Blather \'Round', players_min=2, players_max=6, local_recommended=False, game=PP7),

    GameItem(name='Job Job', players_min=3, players_max=10, local_recommended=False, game=PP8),
    GameItem(name='The Poll Mine', players_min=2, players_max=10, local_recommended=False, game=PP8),
    GameItem(name='Drawful Animate', players_min=3, players_max=10, local_recommended=False, drawing=True, game=PP8),
    GameItem(name='The Wheel of Enormous Proportions', players_min=2, players_max=10, local_recommended=False, game=PP8, image='TWoEP.webp'),
    GameItem(name='Weapons Drawn', players_min=4, players_max=8, local_recommended=False, drawing=True, game=PP8),

    GameItem(name='Paper Pirates', players_min=2, players_max=10, local_recommended=False, game=PartyPack(name='Paper Pirates', app_id=1234220)),
    GameItem(name='Verse Surf', players_min=2, players_max=8, local_recommended=False, game=PartyPack(name='Verse Surf', app_id=1315390)),

    GameItem(name='Use Your Words', players_min=4, players_max=8, local_recommended=False, game=PartyPack(name='Use Your Words', app_id=521350)),
    GameItem(name='What The Dub?!', players_min=1, players_max=6, local_recommended=False, game=PartyPack(name='What The Dub!?', app_id=1495860)),

    GameItem(name='RiffTrax: The Game', players_min=1, players_max=6, local_recommended=False, game=PartyPack(name='RiffTrax: The Game', app_id=1707870)),

    GameItem(name='Trivia Murder Party 2', players_min=1, players_max=8, local_recommended=False, game=PPStarter),
    GameItem(name='Quiplash 3', players_min=3, players_max=8, local_recommended=False, game=PPStarter),
    GameItem(name='Tee K.O.', players_min=3, players_max=8, local_recommended=False, drawing=True, game=PPStarter),

]

ALL_APP_IDS = set([b.game.app_id for b in games])
