from easy_discord_bot.event_handler import EventHandler
import discord

from easy_discord_bot import Commands, Anything


class Panel:
    
    def __init__(self, bot, message):
        self.bot = bot
        self.message = message
        
        self.title = 'Reaction-role panel'
        self.footer = ''
        self.emotes = {}
        
    def load(self, title, footer):
        self.title = title
        self.footer = footer
    
    # Events
    async def on_reaction_add(self, channel_id, message_id, member, emoji):
        await member.add_roles(self.emotes[emoji][0])
        
    async def on_reaction_remove(self, channel_id, message_id, member, emoji):
        await member.remove_roles(self.emotes[emoji][0])
        
    # Commands
    async def set_title(self, title):
        self.title = title
        await self._edit_message()
        self.bot.database.update('react', {'title': title}, f'(panel_id=\'{self.message.id}\')')
        
    async def set_footer(self, footer):
        self.footer = footer
        await self._edit_message()
        self.bot.database.update('react', {'footer': footer}, f'(panel_id=\'{self.message.id}\')')
        
    async def add(self, emote, role, init=False):
        self.emotes[emote] = [role]
        
        self.emotes[emote].append(EventHandler.reaction_add_list.append(self.on_reaction_add, message_id=self.message.id, member_id=Anything, emoji=emote))
        self.emotes[emote].append(EventHandler.reaction_remove_list.append(self.on_reaction_remove, message_id=self.message.id, member_id=Anything, emoji=emote))
        
        if not init:
            await self._edit_message()
            await self.message.add_reaction(emote)
            self.bot.database.insert('roles', {'panel_id': self.message.id, 'emote': f"'{emote}'", 'role_id': role.id})
        
    async def remove(self, emote):
        await self._edit_message()
        await self.message.clear_reaction(emote)
        
        EventHandler.reaction_add_list.remove(self.emotes[emote][1])
        EventHandler.reaction_remove_list.remove(self.emotes[emote][2])
        
        del self.emotes[emote]
        self.bot.database.remove('roles', f'(panel_id=\'self.message.id\') and (emote=\'{emote}\')')
        
    async def _edit_message(self):
        await self.message.edit(
            f'{self.title}\n' + \
            '\n'.join([f'{emote} : {role[0].mention}' for emote, role in self.emotes.items()]) + \
            f'\n{self.footer}'
        )


class React:
    
    def __init__(self, bot):
        self.bot = bot
        self.panels = {}
        
    async def load(self):
        self.bot.logger.log('Loading react...')
        for panel_data in self.bot.database.select('react', ['guild_id', 'channel_id','panel_id', 'title', 'footer'], True):
            guild_id, channel_id, panel_id, title, footer = panel_data.values()
                            
            guild = self.bot.get_guild(guild_id)
            channel = guild.get_channel(channel_id)
            message = await channel.fetch_message(panel_id)
            
            self.panels[message.id] = Panel(self.bot, message)
            self.panels[message.id].load(title, footer)
            self.panels[message.id].event = EventHandler.message_delete_list.append(self.on_panel_deleted, message_id=message.id)
            
            for emotes_data in self.bot.database.select('roles', ['emote', 'role_id'], f'(panel_id=\'{panel_id}\')'):
                emote, role_id = emotes_data.values()
                role = guild.get_role(role_id)
                await self.panels[message.id].add(emote, role, True)
                
    # Events
    async def on_panel_deleted(self, channel_id, message_id):
        panel = self.panels[message_id]
        for _, add_reaction_event, remove_reaction_event in panel.emotes.values():
            EventHandler.reaction_add_list.remove(add_reaction_event)
            EventHandler.reaction_remove_list.remove(remove_reaction_event)
        EventHandler.message_delete_list.remove(panel.event)

        self.bot.database.remove('roles', f'(panel_id=\'{message_id}\')')
        self.bot.database.remove('react', f'(panel_id=\'{message_id}\')')
                
    # Commands
    @Commands.is_admin()
    async def help(self, message):
        await message.channel.send(embed=discord.Embed(
            title = '▬▬▬▬▬ 😱 ▬▬▬▬ React Help ▬▬▬▬ 😱 ▬▬▬▬▬',
            description = 'Automatically gives roles on member add reaction.',
                color = 0x42f560
            ).add_field(
                name = 'Commands :',
                value = f'- **{self.bot.PREFIX}react new** : Create a new reaction-role panel',
                inline=False
            ).add_field(
                name = 'Reply commands :',
                value = f'- **{self.bot.PREFIX}react title <title>** : Set the panel\'s title\n' + \
                        f'- **{self.bot.PREFIX}react footer <footer>** : Set the panel\'s footer\n' + \
                        f'- **{self.bot.PREFIX}react add <server_custom_emoji> <role_mention>** : Add the role associated with the reaction to the panel\n' + \
                        f'- **{self.bot.PREFIX}react remove <server_custom_emoji>** : Remove the reaction (and the role associated with) from the panel\n'
            )
        )
            
    @Commands.is_admin()
    async def new(self, message):
        msg = await message.channel.send('Reaction-role panel')
        self.panels[msg.id] = Panel(self.bot, msg)
        self.panels[msg.id].event = EventHandler.message_delete_list.append(self.on_panel_deleted, message_id=msg.id)
        self.bot.database.insert('react', {'guild_id': msg.guild.id, 'channel_id': msg.channel.id, 'panel_id': msg.id})
        await message.delete()
    
    # Reply commands
    @Commands.is_admin()
    async def title(self, message):
        if (panel := self.panels.get(message.reference.message_id)):
            await panel.set_title(' '.join(message.content.split()[2:]))
            await message.delete()
    
    @Commands.is_admin()
    async def footer(self, message):
        if (panel := self.panels.get(message.reference.message_id)):
            await panel.set_footer(' '.join(message.content.split()[2:]))
            await message.delete()
    
    @Commands.is_admin()
    async def add(self, message):
        if (panel := self.panels.get(message.reference.message_id)):
            emote = message.content.split()[2]
            await panel.add(emote, message.role_mentions[0])
            await message.delete()
    
    @Commands.is_admin()
    async def remove(self, message):
        if (panel := self.panels.get(message.reference.message_id)):
            emote = message.content.split()[2]
            await panel.remove(emote)
            await message.delete()
        
