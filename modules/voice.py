import discord

from easy_discord_bot import Commands, EventHandler, Anything



class Voice:
    
    def __init__(self, bot):
        self.bot = bot
        self.voice_channels = {}
        
    def load(self):
        self.bot.logger.log('Loading voice...')
        
        for voice in self.bot.database.select('voice', ['guild_id', 'channel_id', 'name', 'user_limit'], all=True):
            creator_joined_event = EventHandler.voice_state_update_list.append(self.on_creator_joined, member_id=Anything, after_id=voice['channel_id'])
            creator_delete_event = EventHandler.guild_channel_delete_list.append(self.on_creator_delete, channel_id=voice['channel_id'])
                        
            self.bot.logger.log(f'Loaded creator {voice["channel_id"]} in {voice["guild_id"]}')
            
            children = []
            numbers = []
            for channel in self.bot.database.select('voice_channels', ['id', 'number'], all=True, filter=f"(parent_id='{voice['channel_id']}')"):
                leave_event = EventHandler.voice_state_update_list.append(self.on_voice_leave, member_id=Anything, before_id=channel['id'])
                delete_event = EventHandler.guild_channel_delete_list.append(self.on_channel_delete, channel_id=channel['id'])
                children.append((leave_event, delete_event, channel['number']))
                numbers.append(channel['number'])
                
                self.bot.logger.log(f'- Loaded child {channel["id"]}')
                
            self.voice_channels[voice['channel_id']] = {
                'name': voice['name'],
                'user_limit': voice['user_limit'],
                'creator_event': (creator_joined_event, creator_delete_event),
                'children': children,
                'numbers': numbers,
            }
            
    def get_channel_number(self, creator_id):
        numbers = self.voice_channels[creator_id]['numbers']
        founded = False
        n = 1
        while not founded:
            if n not in numbers:
                founded = True
                self.voice_channels[creator_id]['numbers'].append(n)
            else:
                n += 1
        return n

    # Commands
    @Commands.is_admin()
    async def help(self, message): # r'^voice help$'
        channel_counter = '{}'
        channels = self.bot.database.select('voice', ['channel_id'], True, f"(guild_id='{message.guild.id}')")
        channels_mentions = '\n'.join([f'<#{channel["channel_id"]}>' for channel in channels])
        
        await message.channel.send(embed=discord.Embed(
                title = '▬▬▬▬▬▬ 🔊 ▬▬▬▬▬ Voice Help ▬▬▬▬▬ 🔊 ▬▬▬▬▬▬',
                description = 'Automatically creates voice channels based on member use.',
                color = 0x4797ed
            ).add_field(
                name = 'Current channels :',
                value = f'{channels_mentions if channels_mentions else "None"}',
                inline=False
            ).add_field(
                name = 'Commands :',
                value = f'- **{self.bot.PREFIX}voice new <channel_id>** : Set this channel as a creator channel\n' + \
                        f'- **{self.bot.PREFIX}voice name <channel_id> <name>** : Set the future children channels names *(use "{channel_counter}" to have channel count, max 100 chars)*\n' + \
                        f'- **{self.bot.PREFIX}voice user_limit <channel_id> <0-99>** : Set the future children channels user limit *(0 is infinit)*'
            )
        )

    @Commands.is_admin()
    async def new(self, message): # r'^voice new [0-9]{18}$'
        channel_id = int(message.content.split()[2])
        channel = discord.utils.get(message.guild.channels, id=channel_id)
        if channel:
            if channel_id not in self.voice_channels:
                # Set events
                creator_joined_event = EventHandler.voice_state_update_list.append(self.on_creator_joined, member_id=Anything, after_id=channel_id)
                creator_delete_event = EventHandler.guild_channel_delete_list.append(self.on_creator_delete, channel_id=channel_id)
                
                # Save channel
                self.voice_channels[channel_id] = {
                    'name': 'Voice',
                    'user_limit': 0,
                    'creator_event': (creator_joined_event, creator_delete_event),
                    'children': [],
                    'numbers': [],
                }
                
                self.bot.database.insert('voice', {'guild_id': message.guild.id, 'channel_id': channel_id})
                
                await message.channel.send(f'<#{channel_id}> has been registered !')
            else:
                await message.channel.send('This channel is already registered')
        else:
            await message.channel.send('This channel does not exist')
    
    @Commands.is_admin()
    async def name(self, message): # r'^voice name [0-9]{18} .{1,100}$'
        channel_id = int(message.content.split()[2])
        name = ' '.join(message.content.split()[3:])
        self.voice_channels[channel_id]['name'] = name
        self.bot.database.update('voice', {'name': name}, filter=f"(channel_id='{channel_id}')")
        await message.channel.send(f'Channel name set to {name}')
    
    @Commands.is_admin()
    async def user_limit(self, message): # r'^voice user_limit [0-9]{18} [0-99]$'
        channel_id = int(message.content.split()[2])
        user_limit = int(message.content.split()[3])
        self.voice_channels[channel_id]['user_limit'] = user_limit
        self.bot.database.update('voice', {'user_limit': user_limit}, filter=f"(channel_id='{channel_id}')")
        await message.channel.send(f'User limit set to {user_limit}')
    
    # Events
    async def on_creator_joined(self, member, before, after):
        number = self.get_channel_number(after.channel.id)
        new_channel = await after.channel.category.create_voice_channel(
            name=self.voice_channels[after.channel.id]['name'].format(number),
            user_limit=self.voice_channels[after.channel.id]['user_limit'],
            reason=f'AutoVoice : created by {member.name} ({member.id})'
        )

        # Set events
        leave_event = EventHandler.voice_state_update_list.append(self.on_voice_leave, member_id=Anything, before_id=new_channel.id)
        delete_event = EventHandler.guild_channel_delete_list.append(self.on_channel_delete, channel_id=new_channel.id)

        # Save channel
        self.voice_channels[after.channel.id]['children'].append((leave_event, delete_event, number))
        self.bot.database.insert('voice_channels', {'parent_id': after.channel.id, 'id': new_channel.id, 'number': number})
        self.bot.logger.log(f'Voice : moved {member.name} ({member.id}) : {after.channel.name} ({after.channel.id}) -> {new_channel.name} ({new_channel.id})')

        await member.move_to(new_channel, reason='AutoVoice')

    async def on_creator_delete(self, channel):
        EventHandler.voice_state_update_list.remove(self.voice_channels[channel.id]['creator_event'][0])
        EventHandler.guild_channel_delete_list.remove(self.voice_channels[channel.id]['creator_event'][1])

        children_deleted = len(self.voice_channels[channel.id]['children'])
        for _, delete_event, _ in self.voice_channels[channel.id]['children']:
            await discord.utils.get(self.bot.get_all_channels(), id=delete_event.channel_id).delete()

        self.bot.database.remove('voice', f"(channel_id='{channel.id}')")
        
        self.bot.logger.log(f'Voice : {channel.name} ({channel.id}) deleted : {children_deleted} {"children" if children_deleted > 1 else "child"} deleted')

        del self.voice_channels[channel.id]

    async def on_voice_leave(self, member, before, after):
        if len(before.channel.members) == 0:
            await before.channel.delete(reason=f'AutoVoice : {member.name} ({member.id}) was the last member in the channel')
            
    async def on_channel_delete(self, channel):
        parent_channel_id = self.bot.database.select('voice_channels', ['parent_id'], filter=f"(id='{channel.id}')")['parent_id']

        leave_event, delete_event, number = discord.utils.find(lambda t: t[0].before_id == channel.id, self.voice_channels[parent_channel_id]['children'])
        EventHandler.voice_state_update_list.remove(leave_event)
        EventHandler.guild_channel_delete_list.remove(delete_event)
        
        self.bot.database.remove('voice_channels', f"(id='{channel.id}')")
        
        self.voice_channels[parent_channel_id]['children'].remove((leave_event, delete_event, number))
        self.voice_channels[parent_channel_id]['numbers'].remove(number)
