from discord.ext import tasks
from discord.ext.commands import Bot, Context
from discord import Embed, Colour, Intents, Guild, Role, CategoryChannel
from discord.ui import Button, View
from Secret import bot_token
from LadderboardManip.Classes import *
from enum import Enum
from Matchmaking import matchProctoring
import asyncio
import datetime

intents = Intents.default()
intents.message_content = True
intents.members = True

bot = Bot('!', intents=intents)
bot2 = Bot('-', intents=intents)

target_guild: Guild = None
category_channel: CategoryChannel = None
mod_role: Role = None
master_role: Role = None

def updateSettings():
    settings.GuildID = target_guild.id
    settings.MatchCategoryID = category_channel.id
    settings.ModRoleID = mod_role.id
    settings.CoordinatorRoleID = master_role.id

def dprint(*args, **kwargs):
    print(f'[Baelyth Ladder] {str(datetime.datetime.now())}:', *args, **kwargs)

async def check_valid(ctx: Context):
    if not all([target_guild, category_channel, mod_role, master_role]):
        await ctx.send("Bot is not completely initialized. Please ask moderator to setup the bot correctly first", ephemeral=True)
        dprint(f'{target_guild = }')
        dprint(f'{category_channel = }')
        dprint(f'{mod_role = }')
        dprint(f'{master_role = }')
        return False
    if ctx.guild.id != target_guild.id:
        await ctx.send("Please use this bot in the right server", ephemeral=True)
        return False
    return True

@bot.hybrid_command()
async def join(ctx: Context):
    if not (await check_valid(ctx)):
        return
    new_player = Player.get_player(ctx.author)
    embed = Embed()
    if new_player is None:
        embed.colour = Colour.red()
        embed.description = 'You may not join. You have been banned from ranked matchmaking.'
        await ctx.send(embed=embed)
        return
    if matchProctoring.is_in_match(new_player):
        embed.colour = Colour.red()
        embed.description = "You're already in a match!"
    else:
        success = matchProctoring.matchmaking_queue.add_player(new_player)
        if success:
            embed.colour = Colour.blue()
            embed.description = "You have been added to the queue!"
        else:
            embed.colour = Colour.red()
            embed.description = "You're already in the queue!"
    await ctx.send(embed=embed)

@bot.hybrid_command()
async def leave(ctx: Context):
    if not (await check_valid(ctx)):
        return
    leave_player = Player.get_player(ctx.author)
    if leave_player is None:
        embed.colour = Colour.red()
        embed.description = 'You are not in the queue!'
        await ctx.send(embed=embed)
        return
    if matchProctoring.is_in_match(leave_player):
        embed.colour = Colour.red()
        embed.description = "You're already in a match!"
    else:
        success = matchProctoring.matchmaking_queue.remove_player(leave_player)
        embed = Embed()
        if success:
            embed.colour = Colour.blue()
            embed.description = "You have been removed from the queue!"
        else:
            embed.colour = Colour.red()
            embed.description = "You are not in the queue!"
    await ctx.send(embed=embed)

@bot.hybrid_command()
async def leaderboard(ctx: Context):
    if not (await check_valid(ctx)):
        return
    embed: Embed = await leaderBoard.get_leaderboard(bot.guilds, ctx.guild)
    await ctx.send(embed=embed)

@bot.hybrid_command()
async def setdecaytime(ctx: Context, days: int = 28):
    if not await check_valid(ctx):
        return
    if master_role.id not in [role.id for role in ctx.author.roles]:
        await ctx.send("You don't have the permissions to use this command.", ephemeral=True)
        return
    settings.DecayDays = days
    embed = Embed()
    embed.colour = Colour.blue()
    embed.description = f"Decay time has been set to {days} successfully"
    ctx.send(embed=embed)

@bot.hybrid_command()
async def rankreset(ctx: Context):
    if not await check_valid(ctx):
        return
    if master_role.id not in [role.id for role in ctx.author.roles]:
        await ctx.send("You don't have the permissions to use this command.", ephemeral=True)
        return
    rank_reset()
    embed = Embed()
    embed.colour = Colour.blue()
    embed.description = "Rank successfully reset"
    await ctx.send(embed=embed)

@bot.hybrid_command()
async def banranked(ctx: Context, player: Member):
    if not await check_valid(ctx):
        return
    if mod_role.id not in [role.id for role in ctx.author.roles]:
        await ctx.send("You don't have the permissions to use this command.", ephemeral=True)
        return
    embed = Embed()
    if leaderBoard.archive_member(player.id, True) is None:
        embed.colour = Colour.red()
        embed.description = "Player not found in archives"
    else:
        embed.colour = Colour.blue()
        embed.description = "Player successfully banned from ranked matchmaking"
    await ctx.send(embed=embed)

@bot.hybrid_command()
async def unbanranked(ctx: Context, player: Member):
    if not await check_valid(ctx):
        return
    if mod_role.id not in [role.id for role in ctx.author.roles]:
        await ctx.send("You don't have the permissions to use this command.", ephemeral=True)
        return
    embed = Embed()
    result = leaderBoard.unarchive_member(player.id, False)
    if result is None:
        embed.colour = Colour.red()
        embed.description = "Player not found in archives"
    else:
        embed.colour = Colour.blue()
        embed.description = "Player successfully unbanned from ranked matchmaking"
    await ctx.send(embed=embed)

'''
@bot.hybrid_command()
async def callmod(ctx: Context):
    player = Player.get_player(ctx.author)
    found = False
    for match, data in active_matches.items():
        if player in match.players:
            found = True
    await ctx.send("foo", ephemeral=True)

@bot.hybrid_command()
async def resolve(ctx):
    pass
''' 

@bot.hybrid_command()
async def stats(ctx: Context, member: Member = None):
    dprint(type(member))
    if member is None:
        member = ctx.author
    
    embed = await leaderBoard.get_stats(bot.guilds, member)
    await ctx.send(embed=embed)

async def member_not_found(ctx: Context, exception: Exception):
    dprint(exception)
    await ctx.send("That person is not in the server!", ephemeral=True)

stats.error(member_not_found)

bot.remove_command('help')

@bot.hybrid_command()
async def help(ctx, string = None):
    if not await check_valid(ctx):
        return
    dprint(string)
    embed = Embed()
    embed.title = 'List of commands'
    embed.description = f'Prefix = ! or use slash commands'
    embed.colour = Colour.blue()
    embed.add_field(name='help [None]', value='Show this message!', inline=False)
    embed.add_field(name='alltiers [None]', value='Shows the distribution of tiers', inline=False)
    embed.add_field(name='join [None]', value='join the queue', inline=False)
    embed.add_field(name='leave [None]', value='leave the queue', inline=False)
    embed.add_field(name='stats [None]', value='get your stats', inline=False)
    embed.add_field(name='stats [Member]', value='gets stats of a player', inline=False)
    embed.add_field(name='leaderboard [None]', value='display the top 10 of the leaderboard', inline=False)
    embed.add_field(name='setdecaytime [Days]', value='update the number of days it takes for a player to remain inactive to lose points', inline=False)
    embed.add_field(name='rankreset [None]', value='Creates a new season of ranked', inline=False)
    embed.add_field(name='banranked [Member]', value='bans a player from ranked matchmaking', inline=False)
    embed.add_field(name='unbanranked [Member]', value='unbans a player from ranked matchmaking', inline=False)
    await ctx.send(embed=embed)

@bot.event
async def on_guild_channel_delete(channel):
    if channel in matchProctoring.properly_deleted.keys():
        if not matchProctoring.properly_deleted[channel]:
            for match, channel_n_game in matchProctoring.active_matches.items():
                test_channel, game = channel_n_game
                if channel == test_channel:
                    del matchProctoring.active_matches[match]

@tasks.loop(seconds=12, name="Matchmaking queue loop")
async def matchmaking_loop():
    global target_guild, category_channel
    await matchProctoring.update_active_matches(target_guild, category_channel)

@bot.hybrid_command()
async def sync(ctx: Context):
    if ctx.author.id == 401618139776942080:
        await bot.tree.sync()
        await ctx.send("synced!", ephemeral=True)
    else:
        await ctx.send("You are not the bot creator and may not run this command", ephemeral=True)

@bot.hybrid_command()
async def clear_player_cache(ctx: Context):
    if ctx.author.id == 401618139776942080:
        Player.cached_players = []
        await ctx.send("Done!", ephemeral=True)
    else:
        await ctx.send("You are not the bot creator and may not run this command", ephemeral=True)

@bot.hybrid_command()
async def all_tiers(ctx: Context):
    if not await check_valid(ctx):
        return
    embed = discord.Embed()
    embed.title = "All Tiers"
    embed.description = '''F = 0 - 149
D = 150 - 299
C = 300 - 449 
B = 450 - 599 
A = 600 - 799 
S = 800+'''
    embed.colour = discord.Colour.blue()
    await ctx.send(embed=embed)

@bot.event
async def setup_hook():
    global target_guild, category_channel, mod_role, master_role

    matchmaking_loop.start()

    target_guild = bot.get_guild(settings.GuildID)
    if target_guild is None:
        try:
            target_guild = await bot.fetch_guild(settings.GuildID)
        except NotFound:
            dprint("Failed to get guild")
            exit()
    
    category_channel = bot.get_channel(settings.MatchCategoryID)

    if category_channel is None:
        try:
            category_channel = await bot.fetch_channel(settings.MatchCategoryID)
        except NotFound:
            dprint("Failed to get match category channel")
            exit()
    
    for role in target_guild.roles:
        if role.id == settings.CoordinatorRoleID:
            master_role = role
        if role.id == settings.ModRoleID:
            mod_role = role

    dprint('Done initializing')

@bot.event
async def on_ready():
    dprint("Bot is ready to roll")

'''
async def start_bots():
    await asyncio.gather(bot.start(bot_token), bot2.start(bot_token2))


if __name__ == '__main__':
    asyncio.run(start_bots())

'''
if __name__ == "__main__":
    database_init()
    bot.run(bot_token)
# run the bot with nohup /home/odusa004/Desktop/Personal/Discord/.venv/bin/python3.12 /home/odusa004/Desktop/Personal/Discord/Hypothetical/trial.py
# When you want to kill the bot, do pgrep -a python to find pid
# then do kill [pid]
