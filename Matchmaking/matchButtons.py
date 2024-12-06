from LadderboardManip.Classes import *
from LadderboardManip.dataEnums import *
import discord

character_options = [[]]
for character in Characters:
    if character.value < 0:
        continue
    new_option = discord.SelectOption(label=character.name.replace('_', ' ').title(), value=character.value, emoji=None) # Add emoji later
    character_options[-1].append(new_option)
    if len(character_options[-1]) == 25:
        character_options.append([])

if not character_options[-1]:
    character_options.pop()

starters = [
    Stages.sbf,
    Stages.bf,
    Stages.ps2,
    Stages.tnc,
    Stages.sv
]

base_stage_embed = discord.Embed()
base_stage_embed.title = "Game 1 Stage Bans"
base_stage_embed.color = discord.Colour.blue()

base_outcome_embed = discord.Embed()
base_outcome_embed.color = discord.Colour.blue()
base_outcome_embed.title = "Game 1 Results"

'''
stage_options = []
starter_options = []
for stage in Stages:
    if stage.value < 0:
        continue #useless for now ig
    new_option = discord.Button(label=stage.name.replace('_', ' ').title(), value=stage.value, emoji=None)
    stage_options.append(new_option)

for stage in starters:
    if stage.value < 0:
        continue #useless for now ig
    new_option = discord.SelectOption(label=stage.name.replace('_', ' ').title(), value=stage.value, emoji=None)
    starter_options.append(new_option)
'''

class CallbackButton(discord.ui.Button):
    def __init__(self, *, label, style, callback_func, value):
        super().__init__(label=label, style=style)
        self.value = value
        self._callback = callback_func
    
    async def callback(self, interaction):
        return await self._callback(self, interaction)
    
    async def change_callback(self, new_callback):
        self._callback = new_callback

class CallbackSelect(discord.ui.Select):
    def __init__(self, *, placeholder, options, callback_func):
        super().__init__(placeholder=placeholder, options=options)
        self._callback = callback_func
    
    async def callback(self, interaction):
        return await self._callback(interaction)

class CancelView(discord.ui.View):
    def __init__(self, player_ind, callback, *, timeout = None):
        super().__init__(timeout=timeout)
        self.ind = player_ind
        self._callback_func = callback
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction:discord.Interaction, button:discord.Button):
        button.disabled = True
        button.style = discord.ButtonStyle.grey
        await interaction.response.edit_message(view=self)
        await self._callback_func(interaction, self.ind)

class MainButtons(discord.ui.View):
    def __init__(self, players, *, timeout=7200, void_callback, reset_match_callback):
        super().__init__(timeout=timeout)
        self.void_callback = void_callback
        self.reset_match_callback = reset_match_callback
        self.players = players
        self.players_void_requested = [False, False]
        self.players_reset_requested = [False, False]
    
    async def interaction_check(self, interaction: discord.Interaction):
        return Player.get_player(interaction.user) in self.players

    @discord.ui.button(label="Void",style=discord.ButtonStyle.gray)
    async def void(self, interaction:discord.Interaction, button:discord.ui.Button):
        target_player = Player.get_player(interaction.user)
        ind = self.players.index(target_player)
        other_ind = int(not ind)
        if self.players_void_requested[other_ind]:
            await self.void_callback(target_player)
        else:
            if not self.players_void_requested[ind]:
                self.players_void_requested[ind] = True
                await interaction.channel.send(f'{target_player.name} is requesting to cancel this match. Click the void button to agree to cancel this match.')
            
            await interaction.response.send_message("You are trying to void this match. To cancel this void request, click the button below",
                                                    view=CancelView(ind, self.void_cancel), ephemeral=True)
    
    async def void_cancel(self, interaction:discord.Interaction, ind):
        self.players_void_requested[ind] = False
        await interaction.channel.send(f'{self.players[ind].name} has canceled their void request.')

    @discord.ui.button(label="Reset Match",style=discord.ButtonStyle.gray)
    async def reset_match(self, interaction:discord.Interaction, button:discord.ui.Button):
        target_player = Player.get_player(interaction.user)
        ind = self.players.index(target_player)
        other_ind = int(not ind)
        if self.players_reset_requested[other_ind]:
            await self.reset_match_callback(target_player)
        else:
            if not self.players_reset_requested[ind]:
                self.players_reset_requested[ind] = True
                await interaction.channel.send(f'{target_player.name} is requesting to restart this match. Click the Reset Match button to agree to restart.')
            
            await interaction.response.send_message("You are trying to restart this match. To cancel this restart request, click the button below",
                                                    view=CancelView(ind, self.reset_cancel), ephemeral=True)
    
    async def reset_cancel(self, interaction:discord.Interaction, ind):
        self.players_restart_requested[ind] = False
        await interaction.channel.send(f'{self.players[ind].name} has canceled their void request.')

class CharacterSelectDoubleBlind(discord.ui.View):
    def __init__(self, players, submit_callback, *, timeout=None):
        super().__init__(timeout=timeout)
        self.players = players
        self.tentative_characters: list[Characters] = [None, None]
        self.selected_characters: list[Characters] = [None, None]
        self._submit_callback = submit_callback
        for times, char_options in enumerate(character_options):
            start = times * 25
            end = start + len(char_options) - 1
            new_select = CallbackSelect(placeholder=f'Characters {start} - {end}',
                                        options=char_options, callback_func=self.select_tentative_character)
            self.add_item(new_select)
    
    async def interaction_check(self, interaction: discord.Interaction):
        return Player.get_player(interaction.user) in self.players
    
    async def select_tentative_character(self, interaction: discord.Interaction):
        target_player = Player.get_player(interaction.user)
        player_ind = 0 if target_player == self.players[0] else 1
        selection = Characters(int(interaction.data['values'][0]))
        is_updating = self.tentative_characters[player_ind] is not None
        self.tentative_characters[player_ind] = selection
        if not is_updating:
            message = f"Character set to {selection.name.title().replace('_', ' ')}. Press submit to confirm."
        else:
            message = f"Character updated to {selection.name.title().replace('_', ' ')}. Press submit to confirm"
        await interaction.response.send_message(message, ephemeral=True)
    
    @discord.ui.button(style=discord.ButtonStyle.green, label="Submit")
    async def submit(self, interaction: discord.Interaction, button: discord.ui.Button):
        target_player = Player.get_player(interaction.user)
        player_ind = 0 if target_player == self.players[0] else 1
        if self.tentative_characters[player_ind] is None:
            await interaction.response.send_message("You haven't selected a character", ephemeral=True)
            return
        
        if self.selected_characters[player_ind] is not None:
            self.selected_characters[player_ind] = self.tentative_characters[player_ind]
            await interaction.response.send_message(f'Character selected updated to {self.tentative_characters[player_ind].name}', ephemeral=True)
            return
        
        self.selected_characters[player_ind] = self.tentative_characters[player_ind]

        if self.selected_characters[int(not player_ind)] is None:
            embed = discord.Embed()
            embed.colour = discord.Colour.blue()
            embed.description = f'{target_player.mention} has set their character.'
            await interaction.response.send_message(embed=embed)
            return
        
        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(view=self)
        embed = discord.Embed()
        embed.colour = discord.Colour.blue()
        embed.description = f"{self.players[0].mention}: {self.selected_characters[0].name.replace('_', ' ').title()}\n\
{self.players[1].mention}: {self.selected_characters[1].name.replace('_', ' ').title()}"
        await interaction.channel.send(embed=embed)
        await self._submit_callback(target_player, self.selected_characters)

class CharacterSelectNormal(discord.ui.View):
    def __init__(self, players, first_player, game_num, submit_callback, *, timeout=None):
        super().__init__(timeout=timeout)
        self.players = players
        self.first_player = first_player
        self.has_selected = False
        self.game_num = game_num
        self.tentative_characters: list[Characters] = [None, None]
        self.selected_characters: list[Characters] = [None, None]
        self._submit_callback = submit_callback
        for times, char_options in enumerate(character_options):
            start = times * 25
            end = start + len(char_options) - 1
            new_select = CallbackSelect(placeholder=f'Characters {start} - {end}',
                                        options=char_options, callback_func=self.select_tentative_character)
            self.add_item(new_select)
    
    async def interaction_check(self, interaction: discord.Interaction):
        return Player.get_player(interaction.user) in self.players
    
    async def select_tentative_character(self, interaction: discord.Interaction):
        target_player = Player.get_player(interaction.user)
        player_ind = 0 if target_player == self.players[0] else 1
        expected_player = self.first_player if not self.has_selected else int(not self.first_player)
        if player_ind != expected_player:
            if player_ind == self.first_player:
                await interaction.response.send_message("You already chose a character", ephemeral=True)
                return
            else:
                await interaction.response.send_message("It's not your turn yet", ephemeral=True)
                return
        selection = Characters(int(interaction.data['values'][0]))
        is_updating = self.tentative_characters[player_ind] is not None
        self.tentative_characters[player_ind] = selection
        if not is_updating:
            message = f"Character set to {selection.name.title().replace('_', ' ')}. Press submit to confirm."
        else:
            message = f"Character updated to {selection.name.title().replace('_', ' ')}. Press submit to confirm"
        await interaction.response.send_message(message, ephemeral=True)
    
    async def interaction_check(self, interaction: discord.Interaction):
        return Player.get_player(interaction.user) in self.players
    
    @discord.ui.button(style=discord.ButtonStyle.green, label="Submit")
    async def submit(self, interaction: discord.Interaction, button: discord.ui.Button):
        target_player = Player.get_player(interaction.user)
        player_ind = 0 if target_player == self.players[0] else 1
        expected_player = self.first_player if not self.has_selected else int(not self.first_player)
        other_ind = int(not expected_player)
        if player_ind != expected_player:
            if player_ind == self.first_player:
                await interaction.response.send_message("You already chose a character", ephemeral=True)
                return
            else:
                await interaction.response.send_message("It's not your turn yet", ephemeral=True)
                return
        if self.tentative_characters[player_ind] is None:
            await interaction.response.send_message("You haven't selected a character", ephemeral=True)
            return
        
        if self.selected_characters[player_ind] is not None:
            await interaction.response.send_message(f'You may not change your character selection', ephemeral=True)
            return
        
        self.selected_characters[player_ind] = self.tentative_characters[player_ind]

        if self.selected_characters[int(not player_ind)] is None:
            embed = discord.Embed()
            embed.title = f"Game {self.game_num} Character Selection"
            embed.description = f"{self.players[other_ind].mention}: Select your character"
            embed.color = discord.Colour.blue()
            await interaction.response.edit_message(embed=embed)
            embed2 = discord.Embed()
            embed2.colour = discord.Colour.blue()
            embed2.description = f"{target_player.mention} has chosen {self.selected_characters[player_ind].name.title().replace('_', ' ')}"
            await interaction.channel.send(embed=embed2)
            self.has_selected = True
            return
        
        for child in self.children:
            child.disabled = True
        
        embed = discord.Embed()
        embed.title = f"Game {self.game_num} Character Selection"
        embed.description = f"Characters have been selected!"
        embed.color = discord.Colour.blue()

        await interaction.response.edit_message(embed=embed, view=self)
        embed = discord.Embed()
        embed.colour = discord.Colour.blue()
        embed.description = f"{target_player.mention} has chosen {self.selected_characters[player_ind].name.title().replace('_', ' ')}"
        await interaction.channel.send(embed=embed)
        await self._submit_callback(target_player, self.selected_characters)

class StageSelectStarter(discord.ui.View):
    def __init__(self, players, first_player, finish_callback, *, timeout = None):
        super().__init__(timeout=timeout)
        self.players = players
        self.first_player = first_player
        self.currently_banning = self.players[first_player]
        self.ban_stage = 1
        self.stages_left_to_ban = 1
        self._finish_callback = finish_callback
        for stage in starters:
            new_button = CallbackButton(label = stage.name.title().replace('_', ' '), style=discord.ButtonStyle.green, callback_func=self.disable, value=stage.value)
            self.add_item(new_button)
    
    async def disable(self, button: discord.Button, interaction: discord.Interaction):
        target_player = Player.get_player(interaction.user)
        if self.ban_stage == 1 and self.players[self.first_player] != target_player:
            await interaction.response.send_message("It's not your turn to ban yet", ephemeral=True)
            return
        elif self.ban_stage == 2 and self.players[self.first_player] == target_player:
            await interaction.response.send_message("It's not time to pick yet", ephemeral=True)
            return
        button.style = discord.ButtonStyle.gray
        button.disabled = True

        self.stages_left_to_ban -= 1
        now_picking = False
        if self.stages_left_to_ban == 0:
            self.ban_stage += 1
            if self.ban_stage == 2:
                self.currently_banning = self.players[int(not self.first_player)]
                self.stages_left_to_ban = 2
            else:
                now_picking = True
                self.currently_banning = self.players[self.first_player]
                for child in self.children:
                    await child.change_callback(self.pick_stage)
        
        embed = base_stage_embed.copy()
        if not now_picking:
            embed.description = f'{self.currently_banning.mention}: It\'s your turn to ban.\nBans left: {self.stages_left_to_ban}'
        else:
            embed.description = f'{self.currently_banning.mention}: Please ***pick*** the stage you want to play on.'
        
        await interaction.response.edit_message(embed=embed, view=self)
        await interaction.channel.send(f'{target_player.mention} bans {button.label}')
    
    async def interaction_check(self, interaction: discord.Interaction):
        return Player.get_player(interaction.user) in self.players
    
    def disable_all(self):
        for child in self.children:
            child.style = discord.ButtonStyle.gray
            child.disabled = True
    
    async def pick_stage(self, button: discord.Button, interaction: discord.Interaction):
        target_player = Player.get_player(interaction.user)
        if self.players[self.first_player] != target_player:
            await interaction.response.send_message("You don't pick the stage", ephemeral=True)
            return
        
        self.disable_all()
        button.style = discord.ButtonStyle.green
        
        embed = base_stage_embed.copy()
        embed.description = f'{button.label} has been selected.'

        await interaction.response.edit_message(embed=embed, view=self)
        await interaction.channel.send(f'{target_player.mention} picks {button.label}')
        await self._finish_callback(target_player, Stages(button.value))

class StageSelectNormal(discord.ui.View):
    def __init__(self, players, first_player, game_num, finish_callback, *, timeout = None):
        super().__init__(timeout=timeout)
        self.players = players
        self.first_player = first_player
        self.currently_banning = self.players[first_player]
        self.ban_stage = 1
        self.stages_left_to_ban = 3
        self.game_num = game_num
        self._finish_callback = finish_callback
        for stage in Stages:
            new_button = CallbackButton(label = stage.name.title().replace('_', ' '), style=discord.ButtonStyle.green, callback_func=self.disable, value=stage.value)
            self.add_item(new_button)
    
    async def interaction_check(self, interaction: discord.Interaction):
        return Player.get_player(interaction.user) in self.players
    
    async def disable(self, button: discord.Button, interaction: discord.Interaction):
        target_player = Player.get_player(interaction.user)
        if self.ban_stage == 1 and self.players[self.first_player] != target_player:
            await interaction.response.send_message("It's not your turn to pick yet", ephemeral=True)
            return
        elif self.ban_stage == 2 and self.players[self.first_player] == target_player:
            await interaction.response.send_message("you don't pick the stage", ephemeral=True)
            return
        button.style = discord.ButtonStyle.gray
        button.disabled = True

        self.stages_left_to_ban -= 1
        now_picking = False
        if self.stages_left_to_ban == 0:
            self.ban_stage += 1
            now_picking = True
            self.currently_banning = self.players[int(not self.first_player)]
            for child in self.children:
                await child.change_callback(self.pick_stage)
        
        embed = base_stage_embed.copy()
        embed.title = f"Game {self.game_num} Stage Bans"
        if not now_picking:
            embed.description = f'{self.currently_banning.mention}: It\'s your turn to ban.\nBans left: {self.stages_left_to_ban}'
        else:
            embed.description = f'{self.currently_banning.mention}: Please ***pick*** the stage you want to play on.'
        
        await interaction.response.edit_message(embed=embed, view=self)
        await interaction.channel.send(f'{target_player.mention} bans {button.label}')
    
    def disable_all(self):
        for child in self.children:
            child.style = discord.ButtonStyle.gray
            child.disabled = True
    
    async def pick_stage(self, button: discord.Button, interaction: discord.Interaction):
        target_player = Player.get_player(interaction.user)
        if self.players[self.first_player] == target_player:
            await interaction.response.send_message("You don't pick the stage", ephemeral=True)
            return
        
        self.disable_all()
        button.style = discord.ButtonStyle.green
        
        embed = base_stage_embed.copy()
        embed.title = f"Game {self.game_num} Stage Bans"
        embed.description = f'{button.label} has been selected.'

        await interaction.response.edit_message(embed=embed, view=self)
        await interaction.channel.send(f'{target_player.mention} picks {button.label}')
        await self._finish_callback(target_player, Stages(button.value))

class MidMatchView(discord.ui.View):
    def __init__(self, players, finish_callback, game_num, *, timeout=None):
        super().__init__(timeout=timeout)
        self.players = players
        self.proposed_winner = [None, None]
        self.game_num = game_num
        self._finish_callback = finish_callback
        for ind, player in enumerate(self.players):
            new_button = CallbackButton(label=player.name, style=discord.ButtonStyle.green, callback_func=self.win, value=ind)
            self.add_item(new_button)
    
    async def interaction_check(self, interaction: discord.Interaction):
        return Player.get_player(interaction.user) in self.players
    
    def disable_all(self):
        for child in self.children:
            child.style = discord.ButtonStyle.gray
            child.disabled = True

    async def win(self, button: CallbackButton, interaction: discord.Interaction):
        command_player = Player.get_player(interaction.user)
        ind = self.players.index(command_player)
        embed = base_outcome_embed.copy()
        embed.title = f"Game {self.game_num} Results"
        if self.proposed_winner[int(not ind)] is None:
            if self.players[button.value] == command_player:
                embed.description = f'{command_player.name} has reported a win.'
            else:
                embed.description = f'{command_player.name} has reported a loss.'
            self.proposed_winner[ind] = button.value
        else:
            if self.proposed_winner[int(not ind)] != button.value:
                embed.colour = discord.Colour.red()
                embed.description = 'Players have reported opposite outcomes. Please re-report the result of this match'
                self.proposed_winner = [None, None]
            else:
                embed.description = f'{self.players[button.value].name} has been declared as the winner of this game!'
                self.disable_all()
                button.style = discord.ButtonStyle.green
                await interaction.response.edit_message(embed=embed, view=self)
                await self._finish_callback(command_player, button.value)
                return
        await interaction.response.edit_message(embed=embed)
                
class FinalizeButton(discord.ui.View):
    def __init__(self, players, *, timeout=7200, final_callback):
        super().__init__(timeout=timeout)
        self.final_callback = final_callback
        self.players = players
        self.final_agrees = [False, False]
    
    async def interaction_check(self, interaction: discord.Interaction):
        return Player.get_player(interaction.user) in self.players

    @discord.ui.button(label="Finalize",style=discord.ButtonStyle.green)
    async def finalize(self, interaction:discord.Interaction, button:discord.ui.Button):
        target_player = Player.get_player(interaction.user)
        ind = self.players.index(target_player)
        other_ind = int(not ind)
        await interaction.response.send_message(f'{target_player.name} has confirmed the outcome of this match.')
        if self.final_agrees[other_ind]:
            await self.final_callback(target_player)
        else:
            if not self.final_agrees[ind]:
                self.final_agrees[ind] = True
                
                
