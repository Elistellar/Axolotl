import discord

from easy_discord_bot import Commands, EventHandler, Anything



class Announcement:
    
    def __init__(self, bot):
        self.bot = bot
        self.channel_ids = []
        self.message_events = {}
        self.delete_events = {}
        
    def load(self):
        self.bot.logger.log('Loading announcements...')
        channels = self.bot.database.select('announcement_channels', ['channel_id'], True)
        for channel in channels:
            self.channel_ids.append(channel['channel_id'])
            
            message_event = EventHandler.message_list.append(self.on_message, channel_id=channel['channel_id'], member_id=Anything)
            self.message_events[channel['channel_id']] = message_event
            
            delete_event = EventHandler.guild_channel_delete_list.append(self.on_channel_deleted, channel_id=channel['channel_id'])
            self.delete_events[channel['channel_id']] = delete_event

    async def on_message(self, message):
        await message.publish()
        
    async def on_channel_deleted(self, channel):
        EventHandler.guild_channel_delete_list.remove(self.delete_events[channel.id])
        del self.delete_events[channel.id]
        
        self.bot.database.remove('announcement_channels', f'(channel_id=\'{channel.id}\')')
    
    # Commands
    @Commands.is_admin()
    async def help(self, message):
        channels = self.bot.database.select('announcement_channels', ['channel_id'], True, f'(guild_id=\'{message.guild.id}\')')
        channels_mentions = '\n'.join([f'<#{channel["channel_id"]}>' for channel in channels])
        await message.channel.send(embed=discord.Embed(
                title = '▬▬▬▬ 📢 ▬▬▬▬ Announcement Help ▬▬▬▬ 📢 ▬▬▬▬',
                description = 'Automatically publish messages sent in the declared channels',
                color = 0xeb706c
            ).add_field(
                name = 'Current channels :',
                value = f'{channels_mentions if channels_mentions else "None"}',
                inline=False
            ).add_field(
                name = 'Commands :',
                value = f'- **{self.bot.PREFIX}announcement add <channel_mention>** : Add this channel to the list\n' + \
                        f'- **{self.bot.PREFIX}announcement remove <channel_mention>** : Remove this channel from the list\n'
            )
        )
    
    # Commands
    @Commands.is_admin()
    async def add(self, message):
        channel = message.channel_mentions[0]
        if channel in message.guild.channels and channel.id not in self.channel_ids:
            self.channel_ids.append(channel.id)
            
            message_event = EventHandler.message_list.append(self.on_message, channel_id=channel.id, member_id=Anything)
            self.message_events[channel.id] = message_event
            
            delete_event = EventHandler.guild_channel_delete_list.append(self.on_channel_deleted, channel_id=channel.id)
            self.delete_events[channel.id] = delete_event
            
            self.bot.database.insert('announcement_channels', {'guild_id': message.guild.id, 'channel_id': channel.id})
            
            await message.channel.send(f'{channel.mention} a bien été ajouté à la liste')
    
    # Commands
    @Commands.is_admin()
    async def remove(self, message):
        channel = message.channel_mentions[0]
        if channel in message.guild.channels:
            self.channel_ids.remove(channel.id)
            
            EventHandler.message_list.remove(self.message_events[channel.id])
            del self.message_events[channel.id]
            
            EventHandler.guild_channel_delete_list.remove(self.delete_events[channel.id])
            del self.delete_events[channel.id]
            
            self.bot.database.remove('announcement_channels', f'(channel_id=\'{channel.id}\')')
            
            await message.channel.send(f'{channel.mention} a bien été supprimé de la liste')
