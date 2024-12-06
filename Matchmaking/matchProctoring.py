from LadderboardManip.Classes import *
from enum import Enum
import discord
from Matchmaking import matchmaker
from Matchmaking.matchButtons import *
import asyncio
import datetime

def dprint(*args, **kwargs):
    print(f'[Baelyth Ladder] {str(datetime.datetime.now())}:', *args, **kwargs)

active_matches: dict[Match, list[discord.TextChannel, Game]] = {}
matchmaking_queue = matchmaker.Queue()
properly_deleted: dict[discord.TextChannel, bool] = {}

def is_in_match(member: discord.Member):
    for match in active_matches.keys():
        if member in match.players:
            return True
    return False

async def matches_init(new_matches: list[Match], guild: discord.Guild, category_channel: discord.CategoryChannel):
    for match in new_matches:
        name = f'Match-{match.players[0].name}-vs-{match.players[1].name}'
        new_channel = await guild.create_text_channel(name, category=category_channel)
        properly_deleted[new_channel] = False
        new_game = Game(*match.players)
        active_matches[match] = [new_channel, new_game]
        await match_start(match)

async def update_active_matches(guild: discord.Guild, category_channel: discord.CategoryChannel):
    new_matches = matchmaking_queue.pass_over_queue()
    await matches_init(new_matches, guild, category_channel)

async def match_start(match: Match):
    channel, game = active_matches[match]
    embed = discord.Embed()
    embed.title = "Match Start"
    embed.description = "This is the beginning of this ranked match."
    embed.colour = discord.Colour.blue()
    players = match.players
    await channel.send(f'{players[0].mention}\n{players[1].mention}', embed=embed, view=MainButtons(match.players,
                                                                                                    void_callback=void_match,
                                                                                                    reset_match_callback=reset_match))
    embed.title = "Game 1 Character Selection"
    embed.description = "Select your character"
    await channel.send(embed=embed, view=CharacterSelectDoubleBlind(players, get_characters_first))

async def get_characters_first(player_invoked: Player, characters):
    found = False
    for match, channel_n_game in active_matches.items():
        if player_invoked in match.players:
            found = True
            break
    if not found:
        dprint("Somehow not found (get_characters_first)")
        return
    
    channel, game = channel_n_game
    game: Game
    game.set_char(game.player1, characters[0])
    game.set_char(game.player2, characters[1])

    first_ban_player = 0 if match.players[0].points < match.players[1].points else 1
    

    embed = base_stage_embed.copy()
    embed.description = f'{match.players[first_ban_player].mention}: It\'s your turn to ban.\nBans left: 1'

    await channel.send(embed=embed, view=StageSelectStarter(match.players, first_ban_player, get_stages_first))

async def get_stages_first(player_invoked: Player, stage: Stages):
    found = False
    for match, channel_n_game in active_matches.items():
        if player_invoked in match.players:
            found = True
            break
    if not found:
        dprint("Somehow not found (get_stages_first)")
        return
    
    channel, game = channel_n_game
    game: Game
    game.set_stage(stage)

    embed = base_outcome_embed.copy()
    embed.description = "Please report the match results when you finish your match"
    
    await channel.send(embed = embed, view=MidMatchView(match.players, get_results, 1))

async def get_results(player_invoked: Player, winner_ind):
    found = False
    for match, channel_n_game in active_matches.items():
        if player_invoked in match.players:
            found = True
            break
    if not found:
        dprint("Somehow not found (get_results)")
        return
    
    channel, game = channel_n_game
    game: Game
    game.declare_winner(match.players[winner_ind])
    match.add_game(game)

    if not match.is_finished:
        embed = discord.Embed()
        embed.title = f"Game {sum(match.set_count) + 1} Character Selection"
        embed.description = f"{match.players[winner_ind].mention}: Select your character"
        embed.color = discord.Colour.blue()
        game_num = sum(match.set_count) + 1
        new_game = Game(*match.players)
        active_matches[match] = [channel, new_game]
        await channel.send(embed=embed, view=CharacterSelectNormal(match.players, winner_ind, game_num, get_characters))
    else:
        embed = discord.Embed()
        embed.title = f"Finalize Match"
        embed.description = f"Players: {match.players[0].name}, {match.players[1].name}\nFinal set count: {match.set_count[0]}-{match.set_count[1]}\n\
Winner: {match.players[winner_ind].name}"
        embed.color = discord.Colour.green()
        await channel.send(embed=embed, view=FinalizeButton(match.players, final_callback=finish_match))

async def get_characters(player_invoked: Player, characters):
    found = False
    for match, channel_n_game in active_matches.items():
        if player_invoked in match.players:
            found = True
            break
    if not found:
        dprint("Somehow not found (get_characters)")
        return
    
    channel, game = channel_n_game
    game: Game
    game.set_char(game.player1, characters[0])
    game.set_char(game.player2, characters[1])

    first_ban_player = match.games[-1].winner - 1
    game_num = sum(match.set_count) + 1

    embed = base_stage_embed.copy()
    embed.title = f'Game {game_num} Stage Bans'
    embed.description = f'{match.players[first_ban_player].mention}: It\'s your turn to ban.\nBans left: 3'

    await channel.send(embed=embed, view=StageSelectNormal(match.players, first_ban_player, game_num, get_stages))

async def get_stages(player_invoked: Player, stage: Stages):
    found = False
    for match, channel_n_game in active_matches.items():
        if player_invoked in match.players:
            found = True
            break
    if not found:
        dprint("Somehow not found (get_stages)")
        return
    
    channel, game = channel_n_game
    game: Game
    game.set_stage(stage)

    game_num = sum(match.set_count) + 1

    embed = base_outcome_embed.copy()
    embed.title = f'Game {game_num} Results'
    embed.description = "Please report the match results when you finish your match"
    
    await channel.send(embed = embed, view=MidMatchView(match.players, get_results, game_num))

async def finish_match(player_invoked: Player):
    found = False
    for match, channel_n_game in active_matches.items():
        if player_invoked in match.players:
            found = True
            break
    if not found:
        return
    
    channel, game = channel_n_game
    game: Game
    prior_points = match.players[0].points, match.players[1].points
    prior_tiers = match.players[0].tier, match.players[1].tier
    point_breakdown = match.finalize()

    embed = discord.Embed()
    embed.colour = discord.Colour.green()
    embed.title = "Results"
    order = [0,1] if game.winner == 1 else [1, 0]
    prefixes = ['+', '-']
    outcomes = ['Win', 'Loss']
    for i, prefix, outcome in zip(order, prefixes, outcomes):
        text = f'''**Outcome: {prior_tiers[i]} [{prior_points[i]}] -> {match.players[i].tier} [{match.players[i].points}]**
        [{prefix}{abs(point_breakdown[i][0])} tier pts, {prefix}{abs(point_breakdown[i][1])} raw pts]'''
        title = f'{outcome} - {match.players[i].name}'
        embed.add_field(name=title, value=text)
    
    await channel.send(embed=embed)

    del active_matches[match]

    properly_deleted[channel] = True
    await channel.send("This match has been recorded. Deleting channel in 30 seconds.")
    await asyncio.sleep(30)
    await channel.delete(reason="Match Finished")
    await asyncio.sleep(5)
    del properly_deleted[channel]

async def void_match(player_invoked: Player):
    found = False
    for match, channel_n_game in active_matches.items():
        if player_invoked in match.players:
            found = True
            break
    if not found:
        return
    
    channel, game = channel_n_game
    properly_deleted[channel] = True
    del active_matches[match]
    await channel.send("This match has been voided. Deleting channel")
    await asyncio.sleep(5)
    await channel.delete(reason="Match Voided")
    await asyncio.sleep(5)
    del properly_deleted[channel]

async def reset_match(player_invoked: Player):
    global active_matches

    found = False
    for match, channel_n_game in active_matches.items():
        if player_invoked in match.players:
            found = True
            break
    if not found:
        return
    
    channel, game = channel_n_game

    category = await channel.guild.fetch_channel(channel.category_id)
    guild = channel.guild
    name = channel.name
    
    properly_deleted[channel] = True
    await channel.send("This match is being restarted. This channel is being deleted and a new one is being created.")
    await asyncio.sleep(5)
    await channel.delete(reason="Match Restart")

    new_channel = await guild.create_text_channel(name, category=category)

    del active_matches[match]

    new_match = Match(*match.players)
    new_game = Game(*match.players)

    active_matches[new_match] = [new_channel, new_game]

    await asyncio.sleep(2)
    del properly_deleted[channel]

    await match_start(new_match)


