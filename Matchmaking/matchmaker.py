from LadderboardManip.Classes import *
from collections import namedtuple
import datetime

queueEntrant = namedtuple('queueEntrant', ['player', 'rank', 'points', 'searchWidth', 'startTime'])
SEARCH_WIDTH_INCREASE_TIME = datetime.timedelta(minutes=1)
SEARCH_WIDTH_INCREASE_TIME = datetime.timedelta(seconds = 30)
MAX_SEARCH_WIDTH = 2 # 2 higher or 2 low

def dprint(*args, **kwargs):
    print(f'[Baelyth Ladder] {str(datetime.datetime.now())}:', *args, **kwargs)

def best_fit(target, option1, option2):
    if option1.rank == option2.rank:
        closer = min(option1, option2, key=lambda o: abs(o.points - target.points))
        return closer
    else:
        if abs(option1.rank - target.rank) == abs(option2.rank - target.rank):
            return option1
        else:
            return min(option1, option2, lambda o: abs(o.rank - target.rank))

class Queue:
    def __init__(self):
        self.player_list = []
    
    def add_player(self, new_player: Player):
        if self.exists(new_player):
            return False
        new_entrant = queueEntrant(new_player, determine_rank(new_player.points)[0], new_player.points, 0, datetime.datetime.now())
        self.player_list.append(new_entrant)
        dprint('New queue list', self.player_list)
        self.player_list.sort(key=lambda n: n.startTime)
        return True
    
    def increase_width(self, entrant):
        if entrant.searchWidth == 2:
            return False
        dprint('---\nentrant search width increased', entrant)
        dprint('player list: ', self.player_list)
        self.player_list.remove(entrant)
        entrant = entrant._replace(searchWidth = entrant.searchWidth + 1)
        self.player_list.append(entrant)
        self.player_list.sort(key=lambda n: n.startTime)
        dprint('new player list: ', self.player_list)
        dprint('---')
        return True
    
    def exists(self, player: Player):
        for entrant in self.player_list:
            if entrant.player.id == player.id:
                return True
        return False
    
    def remove_player(self, player: Player):
        if self.exists(player):
            for entrant in self.player_list:
                if entrant.player.id == player.id:
                    self.player_list.remove(entrant)
                    dprint('Player removed: ', entrant)
                    dprint('Player list: ', self.player_list)
                    return True
            return False
        return False
    
    def check_for_matches(self, ind = 0) -> list[Match]:
        if ind >= len(self.player_list) - 1:
            return []
        
        target = self.player_list[ind]
        search_range = range(target.rank - target.searchWidth, target.rank + target.searchWidth + 1)
        curr_found = None
        for i, to_check in enumerate(self.player_list):
            dprint(f'Base: {target.player.name}, Check: {to_check.player.name}')
            if i == ind:
                continue
            dprint(f'Search width: {search_range}, check rank: {to_check.rank}')
            if to_check.rank in search_range:
                if curr_found is None:
                    curr_found = to_check
                    dprint('curr_found updated')
                else:
                    curr_found = best_fit(target, curr_found, to_check)
                    dprint('curr_found updated')
        
        if curr_found is not None:
            new_match = Match(target.player, curr_found.player)
            self.player_list.remove(target)
            self.player_list.remove(curr_found)
            dprint('Match found.\nNew Player List: ', self.player_list)
            return [new_match] + self.check_for_matches(0)
        else:
            return [] + self.check_for_matches(ind + 1)
    
    def update_search_widths(self):
        current_time = datetime.datetime.now()
        for entry in self.player_list:
            if entry.startTime + (1 + entry.searchWidth) * SEARCH_WIDTH_INCREASE_TIME < current_time:
                self.increase_width(entry)
                return
    
    def pass_over_queue(self):
        self.update_search_widths()
        return self.check_for_matches()
