"""
Database module
"""

from typing import Any, Dict

import sqlite3
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
        self, table_name: str = "", table_data_dict: Dict[Any, Any] = OrderedDict()
    ) -> None:
        logger.debug(f" Database: creating table `{table_name}`")

        sql: str = f"CREATE TABLE IF NOT EXISTS {table_name} ("

        # table_data_dict contains keys for either a star (star1 and/or star2) as well as the binary
        # in order to produce a single table, we construct a new dictionary combining the other two
        # but changing the keys in the star* dicts in order to contain an identificator to the star
        # to which it corresponds
        for key, value in table_data_dict.items():
            if value is None:
                sql += f"{key} NULL, "
            else:
                sql += f"{key} {self.DTYPE_MAPPER[type(value)]}, "

        # wrap up command with the final parenthesis
        sql = sql[:-2]
        sql += ");"

        self.execute(sql)
        self.commit()

    def insert_record(
        self,
        table_name: str = "",
        table_data_dict: Dict[Any, Any] = OrderedDict(),
    ) -> None:

        logger.debug(f" Database: inserting record into table `{table_name}`")

        # append row depending on the type of the value
        sql: str = f"INSERT INTO {table_name}"

        # first, find out if any of the elements in the dictionary is an array
        # in which case we need to duplicate items which are not arrays (like an id)
        has_array_elements = False
        n_elements = 0
        for element in table_data_dict.values():
            if isinstance(element, np.ndarray) or isinstance(element, list):
                has_array_elements = True
                n_elements = len(element)
                break

        # get column values
        sql_columm_values_arry = []
        if has_array_elements:
            if n_elements >= 0:
                for k in range(n_elements):
                    _str = "("
                    for value in table_data_dict.values():
                        try:
                            _str += f"{value[k]}, "
                        except Exception:
                            _str += f"{value}, "
                    sql_columm_values_arry.append(f"{_str[:-2]})")
            else:
                logger.error(
                    "error inserting column into database: number of elements should be >= 0"
                )
        else:
            _str = "("
            for value in table_data_dict.values():
                if isinstance(value, str):
                    _str += f"'{value}', "
                else:
                    _str += f"{value}, "
            sql_columm_values_arry.append(f"{_str[:-2]})")

        sql_column_values: str = "VALUES "
        for value in sql_columm_values_arry:
            sql_column_values += f"{value}, "
        sql_column_values = sql_column_values[:-2]

        # now, get column names
        sql_column_names = "("
        for key in table_data_dict.keys():
            sql_column_names += f"{key}, "
        sql_column_names = f"{sql_column_names[:-2]})"

        # write row to MESArun database
        sql2: str = f"{sql} {sql_column_names} {sql_column_values}"

        # commit insertion command to SQLITE database
        self.execute(sql2)
        self.commit()

    def update_record(
        self,
        table_name: str = "",
        table_data_dict: Dict[Any, Any] = OrderedDict(),
        model_id: int = -1,
    ) -> None:

        logger.debug(f" Database: updating record into table `{table_name}`")

        # sql: str = f"UPDATE {table_name} SET "
        # for key, value in table_data_dict.items():
        # # append row depending on the type of the value
        #     if isinstance(value, str):
        #         sql += f"{key} = '{value}', "
        #     else:
        #         sql += f"{key} = {value}, "

        # # write row to MESArun database
        # sql = f"{sql[:-2]} WHERE model_id = {model_id};"

        # append row depending on the type of the value
        sql: str = f"UPDATE {table_name} SET"

        # first, find out if any of the elements in the dictionary is an array
        # in which case we need to duplicate items which are not arrays (like an id)
        has_array_elements = False
        n_elements = 0
        for element in table_data_dict.values():
            if isinstance(element, np.ndarray) or isinstance(element, list):
                has_array_elements = True
                n_elements = len(element)
                break

        # get column values
        sql_columm_values_arry = []
        if has_array_elements:
            if n_elements >= 0:
                for k in range(n_elements):
                    _str = "("
                    for value in table_data_dict.values():
                        try:
                            _str += f"{value[k]}, "
                        except Exception:
                            _str += f"{value}, "
                    sql_columm_values_arry.append(f"{_str[:-2]})")
            else:
                logger.error(
                    "error inserting column into database: number of elements should be >= 0"
                )
        else:
            _str = "("
            for value in table_data_dict.values():
                if isinstance(value, str):
                    _str += f"'{value}', "
                else:
                    _str += f"{value}, "
            sql_columm_values_arry.append(f"{_str[:-2]})")

        sql_column_values: str = "VALUES "
        for value in sql_columm_values_arry:
            sql_column_values += f"{value}, "
        sql_column_values = sql_column_values[:-2]

        # now, get column names
        sql_column_names = "("
        for key in table_data_dict.keys():
            sql_column_names += f"{key}, "
        sql_column_names = f"{sql_column_names[:-2]})"

        # write row to MESArun database
        sql2: str = f"{sql} {sql_column_names} {sql_column_values} WHERE model_id = {model_id}"

        print()
        print("DEBUGGING STOP")
        print(f"sql command: {sql2}")
        print()
        sys.exit()

        # commit insertion command to SQLITE database
        self.execute(sql2)
        self.commit()

    def get_id(self, table_name: str = "", model_name: str = "") -> int:
        """Get identifier of a MESA model

        Parameters
        ----------
        model_name : `str`
            Name of MESA model

        Returns
        -------
        model_id : `int`
            Integer identifier of model_name
        """
        logger.debug(f" Database: getting id for model `{model_name}`")

        model_id = -1

        row = self.fetch(
            table_name=table_name, column_name="id", constraint=f"model_name = '{model_name}'"
        )
        if row[0] is not None:
            model_id = row[0][0]

        return model_id

    def update_model_status(
        self, table_name: str = "", model_name: str = "", status: str = ""
    ) -> None:
        """Update status of a MESA model"""
        logger.debug(f" Database: updating status for model `{model_name}`")

        sql: str = f"UPDATE {table_name} SET status = '{status}' WHERE model_name = '{model_name}';"

        # commit insertion command to SQLITE database
        self.execute(sql)
        self.commit()

    def model_present(self, model_id: int = -1, table_name: str = "") -> bool:
        """Find if model is present in `table_name`"""
        logger.debug(
            f" Database: finding model presence with id `{model_id}` in table `{table_name}`"
        )

        has_data: bool = False

        try:
            row = self.fetch(
                table_name=table_name, column_name="*", constraint=f"model_id = {model_id}"
            )
            if len(row) > 0:
                has_data = True
        except sqlite3.OperationalError:
            pass

        logger.debug(
            f" Database: model with id `{model_id}` in table `{table_name}` (has_data): {has_data}"
        )
        return has_data

    def fetch(self, table_name: str = "", column_name: str = "*", constraint: str = "") -> Any:

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
