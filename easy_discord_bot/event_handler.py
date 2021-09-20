import asyncio
import threading

from discord.partial_emoji import PartialEmoji



class Event:
    
    def __init__(self, func, **kwargs):
        self.func = func
        
        for key, value in kwargs.items():
            setattr(self, key, value)


class EventList:
    
    def __init__(self, *requirements):
        self._list = []
        self.__list_cursor = 0
        
        self._requirements = requirements
        
    def append(self, func, **kwargs):
        for requirement in self._requirements:
            if isinstance(requirement, str) and requirement not in kwargs:
                raise AttributeError(f'{requirement} attribute required')
            elif isinstance(requirement, set) and not requirement | set(kwargs.keys()):
                raise AttributeError(f'{" or ".join(requirement)} attribute required')
            
        event = Event(func, **kwargs)
        self._list.append(event)
        return event
        
    def remove(self, event: Event):
        self._list.remove(event)
    
    def __iter__(self):
        self.__list_cursor = 0
        return self
        
    def __next__(self):
        if self.__list_cursor < len(self._list):
            self.__list_cursor += 1
            return self._list[self.__list_cursor - 1]
        else:
            raise StopIteration()


class EventHandler:
    
    voice_state_update_list   = EventList('member_id', {'after_id', 'before_id'})
    message_delete_list       = EventList('message_id')
    message_edit_list         = EventList('message_id')
    reaction_add_list         = EventList('message_id', 'member_id', 'emoji')
    reaction_remove_list      = EventList('message_id', 'member_id', 'emoji')
    guild_channel_delete_list = EventList('channel_id')
    message_list              = EventList('channel_id', 'member_id')
    reply_list                = EventList('message_id')
    
    @staticmethod
    async def on_voice_state_update(member, before, after):
        loop = asyncio.get_event_loop()
        threading.Thread(target=EventHandler._on_voice_state_update, args=(loop, member, before, after)).start()
    @staticmethod
    def _on_voice_state_update(loop, member, before, after):           
        for event in EventHandler.voice_state_update_list:
            if event.member_id == member.id:
                if (hasattr(event, 'after_id') and after.channel and event.after_id  == after.channel.id) or (hasattr(event, 'before_id') and before.channel and event.before_id == before.channel.id):
                    asyncio.run_coroutine_threadsafe(event.func(member, before, after), loop)
    
    @staticmethod
    async def on_raw_message_delete(channel_id, message_id):
        loop = asyncio.get_event_loop()
        threading.Thread(target=EventHandler._on_raw_message_delete, args=(loop, channel_id, message_id)).start()
    @staticmethod
    def _on_raw_message_delete(loop, channel_id, message_id):
        for event in EventHandler.message_delete_list:
            if event.message_id == message_id:
                asyncio.run_coroutine_threadsafe(event.func(channel_id, message_id), loop)
    
    @staticmethod
    async def on_message_edit(before, after):
        loop = asyncio.get_event_loop()
        threading.Thread(target=EventHandler._on_message_edit, args=(loop, before, after)).start()
    @staticmethod
    def _on_message_edit(loop, before, after):
        for event in EventHandler.message_edit_list:
            if event.message_id == before.channel.id:
                asyncio.run_coroutine_threadsafe(event.func(before, after), loop)
    
    @staticmethod
    async def on_raw_reaction_add(channel_id, message_id, member, emoji):
        loop = asyncio.get_event_loop()
        threading.Thread(target=EventHandler._on_raw_reaction_add, args=(loop, channel_id, message_id, member, emoji)).start()
    @staticmethod
    def _on_raw_reaction_add(loop, channel_id, message_id, member, emoji):
        if isinstance(emoji, PartialEmoji):
            emoji = f'<:{emoji.name}:{emoji.id}>'
        for event in EventHandler.reaction_add_list:
            if event.message_id == message_id \
            and event.member_id == member.id  \
            and event.emoji     == emoji      :
                asyncio.run_coroutine_threadsafe(event.func(channel_id, message_id, member, emoji), loop)
    
    @staticmethod
    async def on_raw_reaction_remove(channel_id, message_id, member, emoji):
        loop = asyncio.get_event_loop()
        threading.Thread(target=EventHandler._on_raw_reaction_remove, args=(loop, channel_id, message_id, member, emoji)).start()
    @staticmethod
    def _on_raw_reaction_remove(loop, channel_id, message_id, member, emoji):
        if isinstance(emoji, PartialEmoji):
            emoji = f'<:{emoji.name}:{emoji.id}>'
        for event in EventHandler.reaction_remove_list:
            if event.message_id == message_id \
            and event.member_id == member.id  \
            and event.emoji     == emoji      :
                asyncio.run_coroutine_threadsafe(event.func(channel_id, message_id, member, emoji), loop)
                
    @staticmethod
    async def on_guild_channel_delete(channel):
        loop = asyncio.get_event_loop()
        threading.Thread(target=EventHandler._on_guild_channel_delete, args=(loop, channel)).start()
    @staticmethod
    def _on_guild_channel_delete(loop, channel):
        for event in EventHandler.guild_channel_delete_list:
            if event.channel_id == channel.id:
                asyncio.run_coroutine_threadsafe(event.func(channel), loop)
                
    @staticmethod
    async def on_message(message):
        loop = asyncio.get_event_loop()
        threading.Thread(target=EventHandler._on_message, args=(loop, message)).start()
    @staticmethod
    def _on_message(loop, message):
        for event in EventHandler.message_list:
            if  event.channel_id == message.channel.id \
            and event.member_id == message.author.id:
                asyncio.run_coroutine_threadsafe(event.func(message), loop)
                
        for event in EventHandler.reply_list:
            if  event.message_id == message.id :
                asyncio.run_coroutine_threadsafe(event.func(message), loop)
