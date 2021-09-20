import asyncio
import datetime
import io
import os

import discord

from .message_pattern import MessagePattern



class Logger:
    
    DISCORD_MAX_MESSAGE_LENGHT = 2000
        
    def __init__(self,
        client: discord.Client,
        console: bool=True,
        txt_folder: str=None,
        discord_channel_id: int=None,
        
        message_format: str=MessagePattern.LOG_MESSAGE_FORMAT,
        files_names_format: str=MessagePattern.LOG_FILES_NAME_FORMAT,
        
        log_sql: bool=False,
        
        discord_ids_on_err: list[int]=[]
    ):
        """An advanced logger

        Args:
            console (bool, optional): Indicate if logs should be showed in the console. Defaults to True.
            txt_folder (str, optional): Indicate the folder where the .log files should be written. None to disable. Defaults to None.
            discord_channel_id (int, optional): Indicate the discord channel id from which dayly log threads will be created. None to disable. Defaults to None.
            message_format (str, optional): The log message format. Defaults to '[{hour}:{minute}:{second}] [{source}]: {message}'.
            files_names_format (str, optional): The log files and thread names format. Defaults to '{year}-{month}-{day}'.
            log_sql (bool, optional): Indicate if sql commands should be logged. Defaults to False.
            discord_ids_on_err (list[int], optional): A list of discord user id which will be mention on error. Defaults to [].
        """
        
        self._methods = []
        if console:
            self._methods.append(print)
            
        if txt_folder:
            self._methods.append(self._txt_print)
            self._txt_folder = txt_folder
            if self._txt_folder[-len(os.sep):] == os.sep:
                self._txt_folder = self._txt_folder[-len(os.sep)]
            
        if discord_channel_id:
            self._client = client
            
            self._lock = asyncio.Lock()
            
            self._methods.append(self._discord_print)
            self._discord_ids_on_err = discord_ids_on_err
            self._discord_channel_id = discord_channel_id
            
        self._message_format = message_format
        self._files_names_format = files_names_format
        
        self._log_sql = log_sql
        
    def _get_file_name(self):
        date = datetime.datetime.now().date()
        
        return self._files_names_format.format(
            year  = date.year,
            month = date.month,
            day   = date.day
        )
    
    def log(self, *args):
        self._write_message('INFO', args)
    
    def sql(self, *args):
        self._write_message('SQL', args)
    
    def err(self, *args):
        self._write_message('ERROR', args)
        
    def _write_message(self, source, args):
        
        time = datetime.datetime.now()
        if time.hour < 10: hour = f'0{time.hour}'
        else: hour = time.hour
        
        if time.minute < 10: minute = f'0{time.minute}'
        else: minute = time.minute
        
        if time.second < 10: second = f'0{time.second}'
        else: second = time.second
        
        message = self._message_format.format(
            hour    = hour,
            minute  = minute,
            second  = second,
            source  = source,
            message = ' '.join([str(arg) for arg in args])
        )
        
        for method in self._methods:
            method(message)
            
    def _txt_print(self, message):
        # Check for a valid filename
        full_path = f'{self._txt_folder}{os.sep}{self._get_file_name()}.log'
        if not os.path.exists(full_path):
            open(full_path, 'w', encoding='utf-8').close()            
        
        # Append to file
        with open(full_path, 'a', encoding='utf-8') as file:
            file.write(message + '\n')

    def _discord_print(self, message):
        loop = asyncio.get_running_loop()
        loop.create_task(self._send_discord_message(message))
        
    async def _get_discord_channel(self):
        init_channel = discord.utils.get(self._client.get_all_channels(), id=self._discord_channel_id)
        thread_channel = discord.utils.get(init_channel.threads, name=self._get_file_name())
        if not thread_channel:
            thread_channel = await init_channel.create_thread(
                name=self._get_file_name(),
                type=discord.ChannelType.public_thread
            )
        return thread_channel

    def discord_mention_users(self, user_ids):
        loop = asyncio.get_running_loop()
        loop.create_task(self._async_discord_mention_users(user_ids))
    
    async def _async_discord_mention_users(self, user_ids):
        message = ' '.join([f"<@{user_id}>" for user_id in user_ids])
        await self._send_discord_message(message, True)
        
    async def _send_discord_message(self, message, raw=False):
        # Get Discord thread
        async with self._lock:
            thread_channel = await self._get_discord_channel()
        
            # Send message
            if len(message) > self.DISCORD_MAX_MESSAGE_LENGHT:
                file = io.BytesIO(message.encode())
                file_message = discord.File(file, filename='too_long_message.log')
                await thread_channel.send(file=file_message)
                    
            else:
                if raw:
                    discord_message = message
                else:
                    discord_message = f'```c\n{message}```'
                
                await thread_channel.send(discord_message)
    