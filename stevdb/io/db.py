"""
Database module
"""

import sqlite3
import time
from collections import OrderedDict

import numpy as np

from .logging import logger


class Database:
    """Database SQL ORM"""

    DTYPE_MAPPER = {
        None: "NULL",
        int: "INTEGER",
        float: "REAL",
        np.float64: "REAL",
        np.ndarray: "REAL",
        str: "TEXT",
        bytes: "BLOB",
        bool: "INTEGER",
    }

    def __init__(self, database_name: str = "") -> None:
        logger.debug(f" Database: connecting to `{database_name}`")

        self.connection = sqlite3.connect(database_name)
        self.cursor = self.connection.cursor()

    def commit(self) -> None:
        self.connection.commit()

    def create_table(
        self, table_name: str = "", table_data_dict: OrderedDict = OrderedDict()
    ) -> None:
        logger.debug(f" Database: creating table `{table_name}`")

        sql: str = f"CREATE TABLE IF NOT EXISTS {table_name} ("

        # table_data_dict contains keys for either a star (star1 and/or star2) as well as the binary
        # in order to produce a single table, we construct a new dictionary combining the other two
        # but changing the keys in the star* dicts in order to contain an identificator to the star
        # to which it corresponds
        for key, value in table_data_dict.items():
            sql += f"{key} {self.DTYPE_MAPPER[type(value)]}, "

        # wrap up command with the final parenthesis
        sql = sql[:-2]
        sql += ");"

        self.execute(sql)
        self.commit()

    def insert_record(
        self, table_name: str = "", table_data_dict: OrderedDict = OrderedDict()
    ) -> None:
        logger.debug(f" Database: inserting record into table `{table_name}`")
        sql: str = f"INSERT INTO {table_name}"
        sql_column_names: str = "("
        sql_column_values: str = "("

        # append row depending on the type of the value
        for key, value in table_data_dict.items():
            if isinstance(value, str):
                sql_column_names += f"{key}, "
                sql_column_values += f"'{value}', "
            else:
                sql_column_names += f"{key}, "
                sql_column_values += f"{value}, "

        # write row to MESArun database
        sql: str = f"{sql} {sql_column_names[:-2]}) VALUES {sql_column_values[:-2]})"

        # commit insertion command to SQLITE database
        self.execute(sql)
        self.commit()

    def get_id(self, table_name: str = "", run_name: str = "") -> int:
        """Get identifier of a MESA model

        Parameters
        ----------
        run_name : `str`
            Name of MESA model
        """
        logger.debug(f" Database: getting id for model `{run_name}`")

        run_id = -1

        row = self.fetch(
            table_name=table_name, column_name="id", constraint=f"run_name = '{run_name}'"
        )
        if row[0] is not None:
            run_id = row[0][0]

        return run_id

    def update_model_status(
        self, table_name: str = "", run_name: str = "", status: str = ""
    ) -> None:
        """Update status of a MESA model"""
        logger.debug(f" Database: updating status for model `{run_name}`")

        sql: str = f"UPDATE {table_name} SET status = '{status}' WHERE run_name = '{run_name}';"

        # commit insertion command to SQLITE database
        self.execute(sql)
        self.commit()

    def model_present(self, run_id: int = -1, table_name: str = "") -> bool:
        """Find if model is present in `table_name`"""
        logger.debug(f" Database: finding model presence with id `{run_id}`")

        has_data: bool = False

        try:
            row = self.fetch(
                table_name=table_name, column_name="*", constraint=f"run_id = {run_id}"
            )
            has_data = True
        except sqlite3.OperationalError:
            pass

        return has_data

    def fetch(self, table_name: str = "", column_name: str = "*", constraint: str = ""):

        sql: str = f"SELECT {column_name} FROM {table_name}"
        if len(constraint) > 0:
            sql += f" WHERE {constraint};"
        else:
            sql += ";"

        logger.debug(f"  fetching sql command: '{sql}'")

        # execute command
        self.execute(sql)
        rows = self.cursor.fetchall()

        return rows

    def execute(self, sql: str = "") -> None:
        logger.debug(f"  executing sql command: '{sql}'")
        self.cursor.execute(sql)

    def __del__(self):
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, ext_type, exc_value, traceback):
        self.cursor.close()
        if isinstance(exc_value, Exception):
            self.connection.rollback()
        else:
            self.commit()
        self.connection.close()
