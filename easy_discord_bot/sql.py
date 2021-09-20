from typing import Any, Union

import mysql.connector

from .logger import Logger



class MySql:
    
    def __init__(self, host: str, port: int, username: str, password: str, database: str, logger: Logger):
        """Handle a connection to a MySql or a MariaDB database

        Args:
            logger (Logger): A class with a "sql(*args)" method used to log every sql call
        """
        
        self._logger = logger
        
        self._connection = mysql.connector.connect(
            host     = host,
            port     = port,
            user     = username,
            password = password,
            database = database
        )
        
        self._cursor = self._connection.cursor(buffered=True, dictionary=True)
        
    def select(self, tab: str, columns: list[str], all: bool=False, filter: str=None) -> Union[dict, list[dict]]:
        """Select one or all rows of a table

        Args:
            tab (str): The table in which the work will be execute
            columns (list[str]): A list of all the columns whose content will be retrieved
            all (bool, optional): A boolean to defined if all rows should be returned or only one. Defaults to False.
            filter (str, optional): The WHERE clause of the sql expression, used to filter rows that must be returned. Defaults to None.

        Returns:
            Union[dict, list[dict]]: If the 'all' argument is set to False, a dict where the keys are the names of the columns. Else, a list of these dicts.
        """
        sql = f'SELECT {", ".join(columns)} FROM {tab}'
        sql = self._add_filter(sql, filter)

        self.execute(sql)
        
        if all:
                return self._cursor.fetchall() 
        else:
            return self._cursor.fetchone()
    
    def insert(self, tab: str, var_dict: dict[str, Any]):
        """Insert a row in a table

        Args:
            tab (str): The table in which the work will be execute
            var_dict (dict[str, Any]): A dict where the keys are the names of the columns
        """
        sql = f'INSERT INTO {tab} ({", ".join([str(key) for key in var_dict.keys()])}) VALUES ({", ".join([str(val) for val in var_dict.values()])});'
        
        self.execute(sql, commit=True)
        
    def remove(self, tab: str, filter: str=None):
        """Remove row(s) from a table

        Args:
            tab (str): The table in which the work will be execute
            filter (str, optional): The WHERE clause of the sql expression, used to filter rows that will be removed. Defaults to None.
        """
        sql = f'DELETE FROM {tab}'
        sql = self._add_filter(sql, filter)
        
        self.execute(sql, commit=True)
    
    def update(self, tab: str, var_dict: dict[str, Any], filter: str=None):
        """Update specified cells in a row

        Args:
            tab (str): The table in which the work will be execute
            var_dict (dict[str, Any]): A dict where the keys are the names of the columns which will be updated
            filter (str, optional): The WHERE clause of the sql expression, used to filter rows that will be updated. Defaults to None.
        """
        set_string = ', '.join([f"{key}='{value}'" for key, value in var_dict.items()])
        sql = f'UPDATE {tab} SET {set_string}'
        sql = self._add_filter(sql, filter)

        self.execute(sql, commit=True)

    @staticmethod
    def _add_filter(sql, filter): # TODO
        if filter is not None:
            where = f' WHERE {filter}'
        else:
            where = ''
        return f'{sql}{where};'
    
    def execute(self, sql, commit: bool=False):
        """Execute sql code

        Args:
            sql ([type]): A sql valid code
            commit (bool, optional): If True, a commit will be executed after the command. Defaults to False.
        """
        self._connection.ping(reconnect=True)
        self._logger.sql(sql)
        self._cursor.execute(sql)
        if commit:
            self._connection.commit()
