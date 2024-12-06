from LadderboardManip.Classes import database_init, Ladderboard, Player, Match, Game, Characters, temp, database, assign_new_match
from LadderboardManip.dataEnums import Characters, Stages
from random import choice

def simulate_set(id1, id2, name1, name2, char1, char2):
    p1_member = temp(id1, name1)
    p2_member = temp(id2, name2)
    p1 = Player.get_player(p1_member)
    p2 = Player.get_player(p2_member)
    new_match = Match(p1, p2)
    while not new_match.is_finished:
        winner = choice([p1, p2])
        new_game = Game(p1, p2)
        new_game.set_char(p1, char1)
        new_game.set_char(p2, char2)
        new_game.set_stage(choice(list(Stages)))
        new_game.declare_winner(winner)
        new_match.add_game(new_game)
    
    new_match.finalize()

if __name__ == '__main__':
    database_init()
    player1_member = temp(347, "Mark")
    player2_member = temp(1200, "Feddy")
    player1 = Player.get_player(player1_member)
    simulate_set(347, 1200, "Mark", "Feddy", Characters.aegis, Characters.banjo)

    cursor = database.execute("SELECT * FROM LadderBoard")
    print(cursor.fetchall())
    print('=' * 8 + '\n\n')
    cursor = database.execute("SELECT * FROM BoardArchive")
    print(cursor.fetchall())