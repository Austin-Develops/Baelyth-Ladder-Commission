from LadderboardManip.dataEnums import *
import sqlite3
from discord import Embed, Guild, Colour, NotFound, Member
import discord
from discord.ext.commands import Bot
from elo_calc import play_game, determine_rank
import datetime
from os import rename, path, mkdir, listdir

IS_BO5 = True
DECAY_MULTIPLIER = 0.8
MIN_PORTION = 0.2 # The portion of total games a character must have in order to count as a mained character
last_row = None

database = sqlite3.connect('ladderboard.db')

def dprint(*args, **kwargs):
    print(f'[Baelyth Ladder] {str(datetime.datetime.now())}:', *args, **kwargs)

def database_init():
    '''Preferably called as program starts or whenever database gets reset. 
    Creates tables used for the program'''
    global database
    database.execute('''CREATE TABLE IF NOT EXISTS LadderBoard(
    player_id INTEGER PRIMARY KEY NOT NULL,
    player_name VARCHAR(32) NOT NULL,
    set_win INTEGER NOT NULL,
    set_lose INTEGER NOT NULL,
    game_win INTEGER NOT_NULL,
    game_lose INTEGER NOT NULL,
    points INTEGER NOT NULL,
    decay_date VARCHAR(32) NOT NULL
) WITHOUT ROWID;''')
    database.execute('''CREATE TABLE IF NOT EXISTS BoardArchive(
    player_id INTEGER PRIMARY KEY NOT NULL,
    player_name VARCHAR(32) NOT NULL,
    set_win INTEGER NOT NULL,
    set_lose INTEGER NOT NULL,
    game_win INTEGER NOT NULL,
    game_lose INTEGER NOT NULL,
    points INTEGER NOT NULL,
    decay_date VARCHAR(32) NOT NULL,
    is_banned INTEGER NOT NULL
) WITHOUT ROWID;''')
    database.execute('''CREATE TABLE IF NOT EXISTS GameList(
    game_id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id INTEGER NOT NULL,
    player1_id INTEGER NOT NULL,
    player1_char INTEGER NOT NULL,
    player2_id INTEGER NOT NULL,
    player2_char INTEGER NOT NULL,
    stage INTEGER NOT NULL,
    victor INTEGER NOT NULL
);''')
    database.execute('''CREATE TABLE IF NOT EXISTS SetList(
    match_id INTEGER PRIMARY KEY,
    date VARCHAR(32) NOT NULL,
    is_bo5 INTEGER NOT NULL,
    player1_id INTEGER NOT NULL,
    player1_game_wins INTEGER NOT NULL,
    player1_points_orig INTEGER NOT NULL,
    player1_points_delta INTEGER NOT NULL,
    player2_id INTEGER NOT NULL,
    player2_game_wins INTEGER NOT NULL,
    player2_points_orig INTEGER NOT NULL,
    player2_points_delta INTEGER NOT NULL,
    victor INTEGER NOT NULL
);''')
    database.commit()

def check_valid(settings_list, ind, type_func, default):
    if len(settings_list) - 1 < ind:
        dprint('Not enough settings. Doing default')
    try:
        return type_func(settings_list[ind])
    except ValueError:
        dprint('Failed to convert', settings_list[ind], 'to', type_func, '\nReturning Default:', default)
        return default

class Settings:
    def __init__(self):
        with open('settings.txt', 'r') as file:
            lines = [line if line[-1] != '\n' else line[:-1] for line in file.readlines()]
            self.lines = lines

        self.__starting = True

        added_settings = []
        
        for line in self.lines:
            if line.strip().startswith('-'):
                added_settings.append(line[1:].strip())
        
        decay_days_arg = check_valid(added_settings, 0, int, 28)
        self.DecayDays = datetime.timedelta(days=decay_days_arg)

        guild_id = check_valid(added_settings, 1, int, 0)
        self.GuildID = guild_id

        matches_category_id = check_valid(added_settings, 2, int, 0)
        self.MatchCategoryID = matches_category_id

        season_coordinator_role_id = check_valid(added_settings, 3, int, 0)
        self.CoordinatorRoleID = season_coordinator_role_id

        mod_role_id = check_valid(added_settings, 4, int, 0)
        self.ModRoleID = mod_role_id

        self.__starting = False

    
    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        if name in ['DecayDays', 'GuildID', 'MatchCategoryID',
                    'CoordinatorRoleID', 'ModRoleID'] and not self.__starting:
            dprint('Change detected in settings')
            self.update()
    
    def update(self):
        data = [self.DecayDays.days, self.GuildID, self.MatchCategoryID]
        ind = 0
        with open('settings.txt', 'w') as file:
            for line in self.lines:
                if line.startswith('-') and ind < len(data):
                    file.write(f'- {data[ind]}')
                    ind += 1
                else:
                    file.write(line)
                file.write('\n')

settings = Settings()

class Ladderboard:
    def __init__(self):
        self.board = None
    
    def archive_member(self, id, is_banned):
        global database
        cursor = database.cursor()
        cursor.execute('''SELECT * FROM LadderBoard
WHERE player_id = ?''', [id])
        result = cursor.fetchone()
        if result == None:
            dprint('Archiving member failed: Member not found')
            return
        result = list(result)
        result.append(int(is_banned))
        cursor.execute('''INSERT INTO BoardArchive(player_id, player_name, set_win, set_lose, game_win, game_lose, points, decay_date, is_banned)
VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)''', result)
        cursor.execute('''DELETE FROM LadderBoard
WHERE player_id = ?''', [id])
        database.commit()
        cursor.close()
    
    def unarchive_member(self, id, only_unbanned: bool = True):
        cursor = database.cursor()
        cursor.execute('''SELECT * FROM BoardArchive
WHERE player_id = ?''', [id])
        result = cursor.fetchone()
        if result == None:
            dprint('Archiving member failed: Member not found')
            return None
        result = list(result)
        is_banned = bool(result.pop())
        if is_banned and only_unbanned:
            return False
        elif is_banned:
            result[-1] = (datetime.datetime.now() + settings.DecayDays).isoformat()
        cursor.execute('''INSERT INTO LadderBoard(player_id, player_name, set_win, set_lose, game_win, game_lose, points, decay_date)
VALUES(?, ?, ?, ?, ?, ?, ?, ?)''', result)
        cursor.execute('''DELETE FROM BoardArchive
WHERE player_id = ?''', [id])
        database.commit()
        cursor.close()
        return 1 if is_banned else True

    async def update(self, emoji_guild_list, guild: Guild):
        global database
        cursor = database.cursor()
        cursor.execute('''SELECT * FROM LadderBoard
ORDER BY
    points DESC,
    player_name DESC
LIMIT 10;''')
        results = cursor.fetchall()
        self.board = results
        self.embed = Embed()
        self.embed.title = "Current Season Standings"
        self.embed.colour = Colour.blue()
        self.embed.description = 'Current Leaderboard for this Season!'
        for pos, result in enumerate(results, 1):
            p_id, p_name, set_win, set_loss, game_win, game_loss, points, decay_date = result
            member = guild.get_member(p_id)
            if member is None:
                try:
                    member = await guild.fetch_member(p_id)
                except NotFound:
                    dprint(f'Player {p_name} ({p_id}) not in server. archiving member')
                    self.archive_member(p_id, False)
                    await self.update(emoji_guild_list, guild)
                    return
            
            player = Player.get_player(member)
            if player._decayed_on_start:
                self.update(emoji_guild_list, guild)
                return
            char_data = player.get_character_data()
            total_games = player.character_data.total_games
            top = list(char_data.keys())
            top.sort(key = lambda char: char_data[char][2], reverse=True)
            top = filter(lambda x: char_data[x][2] > total_games * MIN_PORTION, top)
            top = [str(resolve_emoji(emoji_guild_list, char)) for char in top]

            _, tier = determine_rank(player.points)
            title = f'{pos} - {player.name} ({player.points}) [{tier}]'
            text = f'{player.mention}\nSets: {set_win}/{set_loss}\nGames: {game_win}/{game_loss}\nCharacters: {" ".join(top)}'
            self.embed.add_field(name=title, value=text, inline=False)
        
        cursor.close()

    async def get_leaderboard(self, emoji_guild_list, guild):
        if Match.hasBeenUpdated:
            await self.update(emoji_guild_list, guild)
            Match.hasBeenUpdated = False
        return self.embed
    
    async def get_stats(self, emoji_guild_list, member: Member):
        global database
        player = Player.get_player(member, temporary = True)
        char_data = player.get_character_data()
        total_games = player.character_data.total_games
        
        dprint(char_data)
        dprint(total_games)
        dprint(sum(player.game_record))
        top = list(char_data.keys())
        top.sort(key = lambda char: char_data[char][2], reverse=True)
        top = filter(lambda x: char_data[x][2] > total_games * MIN_PORTION, top)
        top = [str(resolve_emoji(emoji_guild_list, char)) for char in top]

        cursor = database.cursor()
        cursor.execute('''SELECT COUNT(*) FROM LadderBoard
WHERE points > (SELECT points FROM LadderBoard WHERE player_id = ?)''', [player.id])
        position = cursor.fetchone()[0] + 1
        cursor.close()

        _, tier = determine_rank(player.points)
        title = f'{position} - {player.name} ({player.points}) [{tier}]'
        text = f'{player.mention}\nSets: {player.set_record[0]}/{player.set_record[1]}\nGames: {player.game_record[0]}/{player.game_record[1]}\nCharacters: {" ".join(top)}'
        embed = Embed()
        embed.title = title
        embed.description = text
        embed.colour = Colour.blue()
        return embed

leaderBoard = Ladderboard()

class CharacterData:
    def __init__(self):
        self._values = {char: [0,0,0] for char in Characters} #Win, Loss, Total
    
    @staticmethod
    def from_id(player_id):
        global database
        data = CharacterData()
        cursor = database.cursor()
        cursor = cursor.execute('''SELECT * FROM GameList
WHERE player1_id = ? OR player2_id = ?''', [player_id, player_id])
        all_games = cursor.fetchall()
        cursor.close()
        for _, _, p1_id, p1_char, p2_id, p2_char, _, victor in all_games:
            ind = int(player_id == p1_id)
            real_char = Characters((p2_char, p1_char)[ind])
            changing_ind = int(victor % 2 != ind)
            data._values[real_char][changing_ind] += 1
            data._values[real_char][2] += 1
            data._values[Characters.total][changing_ind] += 1
            data._values[Characters.total][2] += 1
        
        return data
    
    def game_update(self, char: Characters, is_win):
        is_loss = not is_win
        self._values[char][int(is_loss)] += 1
        self._values[char][2] += 1
        self._values[Characters.total][changing_ind] += 1
        self._values[Characters.total][2] += 1

    def get_data(self):
        return {k: v for k, v in self._values.items() if v[2] > 0 and k.value >= 0}
    
    @property
    def total_games(self):
        return self._values[Characters.total][2]

    
class Player:
    MAX_CACHE = 30
    cached_players: list['Player'] = [] # Keep up to 30 players in memory so repeated lookups aren't necessary

    def __init__(self, playerid, name, points, s_record, g_record, decay_date):
        self.id: int = playerid
        self.name: str = name
        self.points: int = points
        self.set_record: list[int, int] = s_record
        self.game_record: list[int, int] = g_record
        self.character_data: CharacterData | None = None
        self.decay_date: datetime.datetime = decay_date
        self._decayed_on_start = False
        now = datetime.datetime.now()
        if now > self.decay_date:
            self._decayed_on_start = True
            while now > self.decay_date:
                self.points *= DECAY_MULTIPLIER
                self.decay_date += settings.DecayDays
            self.update()

    @property
    def mention(self):
        return f'<@{self.id}>'
    
    @property
    def tier(self):
        return determine_rank(self.points)[1]
    
    @staticmethod
    def cache_player(p: 'Player'):
        if p in Player.cached_players:
            Player.cached_players.remove(p)
        Player.cached_players.insert(0, p)
        if len(Player.cached_players) > Player.MAX_CACHE:
            Player.cached_players.pop()
    
    @staticmethod
    def get_player(member: Member, *, temporary = False):
        '''Gets a player either from cache, if present, or from database'''
        global database
        # Attempt to get them from cache
        found = False
        for player in Player.cached_players:
            if player.id == member.id:
                new_player = player
                found = True
                break
        

        if not found:
            # Member not in found
            worked = leaderBoard.unarchive_member(member.id, not temporary)
            if worked == False:
                return None
            cursor = database.cursor()
            cursor = cursor.execute('''SELECT * FROM LadderBoard
    WHERE player_id = ?''', [member.id])
            data = cursor.fetchone()
            if data is None:
                # Player isn't in database. Must be new. Adding them
                decay_date = datetime.datetime.now() + settings.DecayDays
                new_player = Player(member.id, member.display_name, 0, [0, 0], [0, 0], decay_date)
                new_player.character_data = CharacterData()
                cursor.execute('''INSERT INTO LadderBoard(player_id, player_name, set_win, set_lose, game_win, game_lose, points, decay_date)
    VALUES(?, ?, ?, ?, ?, ?, ?, ?)''', [member.id, member.display_name, 0, 0, 0, 0, 0, decay_date])
                database.commit()
                cursor.close()
            else:
                player_id, player_name, set_win, set_lose, game_win, game_lose, points, decay_date_str = data
                decay_date = datetime.datetime.fromisoformat(decay_date_str)
                new_player = Player(player_id, player_name, points, [set_win, set_lose], [game_win, game_lose], decay_date)

        if not temporary:   
            Player.cache_player(new_player)
            if new_player.name != member.display_name:
                new_player.name = member.display_name
                new_player.update()
        
        if temporary and not found and worked:
            leaderBoard.archive_member(member.id, worked == 1)
        return new_player

    def __str__(self):
        return self.name
        
    def __eq__(self, other):
        if type(other) in [Player, Member]:
            return self.id == other.id
        return False
    
    def get_character_data(self):
        if not self.character_data:
            self.character_data = CharacterData.from_id(self.id)
        
        return self.character_data.get_data()

    def add_game(self, char: Characters, is_win):
        is_loss = not is_win
        if self.character_data is not None:
            self.character_data.game_update(char, is_win)
        
        self.game_record[int(is_loss)] += 1
    
    def add_set(self, is_win, delta_points):
        is_loss = not is_win
        self.set_record[int(is_loss)] += 1
        self.points += delta_points
        self.decay_date = datetime.datetime.now() + settings.DecayDays
        self.update()
    
    def update(self):
        decay_date_str = self.decay_date.isoformat()
        cursor = database.cursor()
        cursor.execute('''UPDATE LadderBoard
SET player_name = ?,
    set_win = ?,
    set_lose = ?,
    game_win = ?,
    game_lose = ?,
    points = ?,
    decay_date = ?
WHERE player_id == ?
    ''', [self.name, *self.set_record, *self.game_record, self.points, decay_date_str, self.id])
        database.commit()
        cursor.close()

class Game:
    def __init__(self, player1, player2):
        self.player1: Player = player1
        self.player2: Player = player2
        self.stage: Stages | None = None
        self.winner: int = None
        self.char1: Characters = None
        self.char2: Characters = None
    
    def set_stage(self, stage: Stages):
        self.stage = stage
    
    def declare_winner(self, player: Player):
        if player not in [self.player1, self.player2]:
            raise IndexError(f'{player.name} not found in players')
        self.winner = 1 if player == self.player1 else 2
    
    def set_char(self, player, char):
        assert player in (self.player1, self.player2)
        if player == self.player1:
            self.char1 = char
        else:
            self.char2 = char
    
    def finalize(self, match_id):
        self.player1.add_game(self.char1, self.winner == 1)
        self.player2.add_game(self.char2, self.winner == 2)
        database.execute('''INSERT INTO GameList(match_id, player1_id, player1_char, player2_id, player2_char, stage, victor)
VALUES(?, ?, ?, ?, ?, ?, ?);''', [match_id, self.player1.id, self.char1.value, self.player2.id, self.char2.value, \
                               self.stage.value, self.winner])
        database.commit()

class Match:
    hasBeenUpdated = True
    last_match_id = None

    def __init__(self, player1, player2):
        self.players: list[Player] = player1, player2
        self.games: list[Game] = []

    def add_game(self, game: Game):
        if not self.is_finished:
            self.games.append(game)
    
    @property
    def set_count(self):
        to_return = [0,0]
        for game in self.games:
            if game.winner is not None:
                to_return[game.winner - 1] += 1
        return to_return

    @property
    def is_finished(self):
        if not self.games:
            return False
        if self.games[-1].winner is None:
            return False
        return 3 in self.set_count if IS_BO5 else 2 in self.set_count
    
    def finalize(self):
        assert self.is_finished
        new_match_id = assign_new_match()
        curr_date = datetime.datetime.now().isoformat()
        victor = self.games[-1].winner
        point_breakdown, all_delta = play_game(self.players[0].points, self.players[1].points, victor == 1)
        args = [
            new_match_id,
            curr_date,
            int(IS_BO5),
            self.players[0].id,
            self.set_count[0],
            self.players[0].points,
            all_delta[0],
            self.players[1].id,
            self.set_count[1],
            self.players[1].points,
            all_delta[1],
            victor
        ]

        for game in self.games:
            game.finalize(new_match_id)

        database.execute('''INSERT INTO SetList(match_id, date, is_bo5, player1_id, player1_game_wins, player1_points_orig, \
player1_points_delta, player2_id, player2_game_wins, player2_points_orig, player2_points_delta, victor)
VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', args)
        database.commit()

        self.players[0].add_set(victor == 1, all_delta[0])
        self.players[1].add_set(victor == 2, all_delta[1])

        Match.hasBeenUpdated = True

        return point_breakdown


def assign_new_match():
    cursor = database.cursor()
    cursor.execute('''SELECT match_id FROM SetList ORDER BY match_id DESC LIMIT 1''')
    result = cursor.fetchone()
    cursor.close()
    if result is None:
        return 1
    return 1 + result[0]

def rank_reset():
    global database
    database.close()
    if not path.exists('Archive'):
        mkdir("Archive")
    date_str = datetime.date.today().isoformat()
    path_name = f"Archive/Ladderboard ({date_str}).db"
    if path.exists(path_name):
        num = 1
        path_name = f"Archive/Ladderboard ({date_str}) ({num}).db"
        while path.exists(path_name):
            num += 1
            path_name = f"Archive/Ladderboard ({date_str}) ({num}).db"
    rename("ladderboard.db", path_name)
    database = sqlite3.connect('ladderboard.db')
    database_init()
    Match.hasBeenUpdated = True
    Player.cached_players = []

def resolve_emoji(emoji_guild_list, character: Characters):
    for guild in emoji_guild_list:
        result = discord.utils.get(guild.emojis, name=character.name)
        if result is not None:
            return result
    raise discord.NotFound(f"Emoji {character.name} not found")

if __name__ == '__main__':
    database_init()
    player1 = temp(347)
    player2 = temp(1200)
    new_game = Game(player1, player2)
    new_game.set_stage(Stages.bf)
    new_game.set_char(player1, Characters.chrom)
    new_game.set_char(player2, Characters.poketrainer)
    new_game.declare_winner(player1)
    new_game.finalize(assign_new_match())

    cursor = database.execute("SELECT * FROM GameList")
    dprint(cursor.fetchall())
    dprint('=' * 8 + '\n\n')

