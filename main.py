import traceback
import io
import contextlib

import discord

import easy_discord_bot

from modules.voice import Voice
from modules.announcement import Announcement
from modules.react import React


class Axolotl(easy_discord_bot.Bot):
    
    TOKEN = 'TOKEN'
    PREFIX = '!'
    
    LOG_SQL = True
    LOG_DISCORD_CHANNGEL_ID = None
    LOG_DISCORD_IDS_ON_ERR = []
    
    MYSQL_HOST = 'localhost'
    MYSQL_PORT = 3306
    MYSQL_DATABASE = 'axolotl'
    MYSQL_USERNAME = ''
    MYSQL_PASSWORD = ''
    
    ALLOWED_PYTHON_MODULES = [
        'math',
        'random',
        're',
        'json',
        'time',
    ]

    def __init__(self):
        super().__init__()
        
        self.python_syntax_image = discord.File('python_syntax.png')
        
        self.voice = Voice(self)
        self.announcement = Announcement(self)
        self.react = React(self)
        
        allowed_python_module_string = '|'.join([f'{module} ' for module in self.ALLOWED_PYTHON_MODULES])
        allowed_python_module_lenght = '{0,' + str(len(self.ALLOWED_PYTHON_MODULES)) + '}'
        python_command_regex = f'^py ({allowed_python_module_string}){allowed_python_module_lenght}?```python\n(.|\n)+\n```$'

        commands = {
            r'^voice help$': self.voice.help,
            r'^voice new [0-9]{18}$': self.voice.new,
            r'^voice name [0-9]{18} .{1,100}$': self.voice.name,
            r'^voice user_limit [0-9]{18} [0-99]$': self.voice.user_limit,
            
            r'^announcement help$': self.announcement.help,
            r'^announcement add <#[0-9]{18}>$': self.announcement.add,
            r'^announcement remove <#[0-9]{18}>$': self.announcement.remove,
            
            r'^react help$': self.react.help,
            r'^react new$': self.react.new,
            
            f'^py help$': self.python_help,
            fr'{python_command_regex}': self.exec_python,
            r'help$': self.help,
        }
        reply_commands = {
            r'^react title .+': self.react.title,
            r'^react footer .+': self.react.footer,
            r'^react add <:[a-zA-Z0-9_]{1,32}:[0-9]{18}> <@&[0-9]{18}>$': self.react.add,
            r'^react remove <:[a-zA-Z0-9_]{1,32}:[0-9]{18}>$': self.react.remove,
        }
        self.set_commands(commands, reply_commands)
    
    async def on_ready(self):
        self.logger.log('Axolotl is waking up')
        self.voice.load()
        self.announcement.load()
        await self.react.load()
        self.logger.log('Axolotl ready !')
        
    # Commands
    async def help(self, message):
        if message.author.guild_permissions.administrator:
            await message.channel.send(
                embed=discord.Embed(
                    title = '▬▬▬▬ 🔧 ▬▬▬▬ Axolotl Help ▬▬▬▬ 🔧 ▬▬▬▬',
                    description = 'Modules :\n' + \
                    f'- **{self.PREFIX}voice help** : Auto-generated voice channels\n' + \
                    f'- **{self.PREFIX}react help** : Reaction-roles messages\n' + \
                    f'- **{self.PREFIX}announcement help** : Auto message publishing in announcement channels\n' + \
                    '\n' + \
                    f'Commands :\n' + \
                    f'- **{self.PREFIX}py help** : Send information about how to use the `py` command',
                    color = 0xd576e8
                ).set_footer(
                    text = 'by <@357949814782033920>'
                )
            )
        else:
            await message.channel.send(
                embed=discord.Embed(
                    title = '▬▬▬▬ 🔧 ▬▬▬▬ Axolotl Help ▬▬▬▬ 🔧 ▬▬▬▬',
                    description = 'Commands :\n' + \
                    f'- **{self.PREFIX}py help** : Send information about how to use the `py` command',
                    color = 0xd576e8
                ).set_footer(
                    text = 'by <@357949814782033920>'
                )
            )
            
    
    async def python_help(self, message):
        await message.channel.send(embed=discord.Embed(
                title = '▬▬▬▬▬ 🐍 ▬▬▬▬▬ Python Help ▬▬▬▬▬ 🐍 ▬▬▬▬▬',
                description = 'Execute python code\n' + \
                              '`breakpoint()`, `compile()`, `eval()`, `exec()`, `id()`, `input()` and `open()` functions are disabled\n' + \
                              ', '.join(self.ALLOWED_PYTHON_MODULES) + ' libraries are allowed',
                color = 0xd576e8
            )
        )
        await message.channel.send(file=self.python_syntax_image)
    
    async def exec_python(self, message): # r'^py (module1 |module2...){0,nb_modules} ```python\n(.|\n)+\n```$'
        modules = message.content.split('\n')[0].split()[1:-1]
        python_code = '\n'.join(message.content.split('\n')[1:-1])
        
        for line in python_code.split('\n'):
            if 'import' in line:
                await message.reply(f'Imports are disabled, enter `{self.PREFIX}help` to see how to import a module with {self.user.mention}')
                return
            
            if 'breakpoint' in line \
            or 'compile'    in line \
            or 'eval'       in line \
            or 'exec'       in line \
            or 'input'      in line \
            or 'id'         in line \
            or 'open'       in line:
                await message.reply('`breakpoint()`, `compile()`, `eval()`, `exec()`, `id()`, `input()` and `open()` functions are disabled')
                return
            
        for module in modules:
            python_code = f'import {module}\n' + python_code
        
        # Exec
        try:
            f = io.StringIO()
            with contextlib.redirect_stdout(f):
                exec(python_code)
            ret = f.getvalue()
        except Exception as e:
            traceback_lines = traceback.format_exc().split("\n")
            traceback_str = traceback_lines[0] + '\n' + '\n'.join(traceback_lines[3:])
            await message.reply(f'```python\n{traceback_str}\n```')
        else:
            str_prints = ''.join([f'>> {line}\n' for line in ret.split('\n') if line != ''])
            ret = f'```python\n{str_prints}\n```'
            await message.reply(ret)

if __name__ == '__main__':
    bot = Axolotl()
    bot.run()