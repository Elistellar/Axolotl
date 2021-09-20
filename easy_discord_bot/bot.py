import traceback
from typing import Callable, Pattern

import discord

from .commands import Commands
from .event_handler import EventHandler
from .logger import Logger
from .message_pattern import MessagePattern
from .sql import MySql


class Bot(discord.Client):
    
    TOKEN = None
    PREFIX = None
    
    MYSQL_HOST = None
    MYSQL_PORT = None
    MYSQL_USERNAME = None
    MYSQL_PASSWORD = None
    MYSQL_DATABASE = None
    
    LOG_CONSOLE = True
    LOG_FOLDER = None
    LOG_DISCORD_CHANNGEL_ID = None
    LOG_MESSAGE_FORMAT = MessagePattern.LOG_MESSAGE_FORMAT
    LOG_FILES_NAME_FORMAT = MessagePattern.LOG_FILES_NAME_FORMAT
    LOG_SQL = False
    LOG_DISCORD_IDS_ON_ERR = []
        
    def __init__(self, intents: discord.Intents=discord.Intents.default()):
        super().__init__(intents=intents)
        
        Commands.PREFIX = self.PREFIX
                
        self.logger = Logger(
            client             = self,
            console            = self.LOG_CONSOLE,
            txt_folder         = self.LOG_FOLDER,
            discord_channel_id = self.LOG_DISCORD_CHANNGEL_ID,
            message_format     = self.LOG_MESSAGE_FORMAT,
            files_names_format = self.LOG_FILES_NAME_FORMAT,
            log_sql            = self.LOG_SQL,
            discord_ids_on_err = self.LOG_DISCORD_IDS_ON_ERR
        )
        
        if self.MYSQL_HOST and self.MYSQL_PORT and self.MYSQL_USERNAME and self.MYSQL_PASSWORD and self.MYSQL_DATABASE:
            self.database = MySql(
                host     = self.MYSQL_HOST,
                port     = self.MYSQL_PORT,
                username = self.MYSQL_USERNAME,
                password = self.MYSQL_PASSWORD,
                database = self.MYSQL_DATABASE,
                logger   = self.logger
            )
            
    def set_commands(self, commands: dict[Pattern, Callable[..., None]], reply_commands: dict[Pattern, Callable[..., None]]={}):
        for syntax, command in commands.items():
            Commands.add(syntax, command)
        for syntax, command in reply_commands.items():
            Commands.add(syntax, command, True)

    def run(self):
        super().run(self.TOKEN)
      
    # Discord events
    async def on_error(self, event, *args, **kwargs):
        self.logger.err(traceback.format_exc())
        if self.LOG_DISCORD_CHANNGEL_ID and self.LOG_DISCORD_IDS_ON_ERR:
            self.logger.discord_mention_users(self.LOG_DISCORD_IDS_ON_ERR)
            
    async def on_voice_state_update(self, member, before, after):
        await EventHandler.on_voice_state_update(member, before, after)
            
    async def on_raw_message_delete(self, payload):
        await EventHandler.on_raw_message_delete(payload.channel_id, payload.message_id)
        
    async def on_raw_bulk_message_delete(self, payload):
        for message_id in payload.message_ids:
            await EventHandler.on_raw_message_delete(payload.channel_id, message_id)
            
    async def on_message_edit(self, before, after):
        await EventHandler.on_message_edit(before, after)
        
    async def on_raw_reaction_add(self, payload):
        if payload.user_id != self.user.id:
            await EventHandler.on_raw_reaction_add(payload.channel_id, payload.message_id, payload.member, payload.emoji)
        
    async def on_raw_reaction_remove(self, payload):
        if payload.user_id != self.user.id:
            guild = discord.utils.get(self.guilds, id=payload.guild_id)
            member = await guild.fetch_member(payload.user_id)
            await EventHandler.on_raw_reaction_remove(payload.channel_id, payload.message_id, member, payload.emoji)
            
    async def on_message(self, message):
        await EventHandler.on_message(message)
        
        if message.author != self.user:
            if message.content.startswith(self.PREFIX):
                await Commands.run(message)
                
    async def on_guild_channel_delete(self, channel):
        await EventHandler.on_guild_channel_delete(channel)
