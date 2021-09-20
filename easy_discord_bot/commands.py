import re
from typing import Pattern

import discord


class Commands:
    
    PREFIX = None
    
    _commands = {}
    _reply_commands = {}
    
    @staticmethod
    def add(syntax, func, reply=False):
        s = re.compile(syntax)
        if reply:
            Commands._reply_commands[s] = func
        else:
            Commands._commands[s] = func
    
    @staticmethod
    async def run(message):
        for syntax, command in Commands._commands.items():
            if syntax.match(message.content[len(Commands.PREFIX):]):
                await command(message)
                break
            
        if message.reference:
            for syntax, command in Commands._reply_commands.items():
                if syntax.match(message.content[len(Commands.PREFIX):]):
                    await command(message)
                    break
            
    @staticmethod
    def is_admin():
        def decorator(func):
            async def wrapped_func(*args, **kwargs):
                for arg in args:
                    if isinstance(arg, discord.Message):
                        message = arg
                        break
                else:
                    raise SyntaxError('Invalid use of @is_valid_syntax: no discord.Message object founded in function arguments')
                
                if message.author.guild_permissions.administrator:
                    return await func(*args, **kwargs)
            return wrapped_func
        return decorator