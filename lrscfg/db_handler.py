import sqlite3
import csv
import os
from datetime import datetime
from prettytable import PrettyTable
from lrscfg.config import Config

class DB_Handler:
    def __init__(self):
        config_settings = Config().parse_yaml()
        db_path = config_settings["db_path"]
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS moas_versions (
                config_id INTEGER PRIMARY KEY AUTOINCREMENT,
                version TEXT,
                tag TEXT,
                is_active INTEGER DEFAULT 0
            )
        ''')
        # FOAS versions table (parallel to moas_versions)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS foas_versions (
                config_id INTEGER PRIMARY KEY AUTOINCREMENT,
                version TEXT,
                tag TEXT,
                is_active INTEGER DEFAULT 0
            )
        ''')

    def update_channels_table(self, table_name, column_names, data_types):
        """Create or alter a channels table named `table_name`.

        Arguments:
        - table_name: name of the SQL table to create/alter (e.g. 'moas_channels' or 'foas_channels').
        - column_names: iterable of column names (strings)
        - data_types: iterable of SQL data type strings aligned with column_names

        This replaces the previous duplicated moas/foas updaters and is the single
        location to manage channel-table schema.
        """
        if not isinstance(table_name, str):
            raise TypeError('table_name must be a string')

        self.cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
        table_exists = self.cursor.fetchone()

        if not table_exists:
            create_table_query = f"CREATE TABLE {table_name} (\n    config_id INTEGER,\n"
            for i in range(len(column_names)):
                create_table_query += f'    {column_names[i]} {data_types[i]},\n'
            # reference the appropriate versions table
            if table_name.startswith('foas'):
                fk = 'foas_versions'
            else:
                fk = 'moas_versions'
            create_table_query += f'    FOREIGN KEY (config_id) REFERENCES {fk}(config_id)\n)'
            self.cursor.execute(create_table_query)
        else:
            for i in range(len(column_names)):
                self.cursor.execute(f"PRAGMA table_info('{table_name}')")
                existing_columns = [row[1] for row in self.cursor.fetchall()]
                if column_names[i] not in existing_columns:
                    self.cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_names[i]} {data_types[i]}")


    def import_configuration(self, csv_file, tag):
        # Extract version tag from file name
        version = os.path.splitext(os.path.basename(csv_file))[0]
        if version.startswith('MOAS_'):
            version = version[5:]  # Remove 'MOAS_' prefix
        else:
            raise ValueError("Invalid MOAS filename")
        
        # Check if version tag already exists in the database
        self.cursor.execute('SELECT version FROM moas_versions WHERE version = ?', (version,))
        existing_version = self.cursor.fetchone()
        
        if not existing_version:
            self.cursor.execute('INSERT INTO moas_versions (version,tag) VALUES (?,?)', (version,tag))
            config_id = self.cursor.lastrowid
            
            with open(csv_file, 'r') as file:
                csv_reader = csv.reader(file)
                headers = next(csv_reader)
                data_types = []
                for _ in headers:
                    data_types.append('TEXT')  # Default data type is TEXT
                for row in csv_reader:
                    for i, value in enumerate(row):
                        try:
                            int(value)
                            data_types[i] = 'INTEGER'
                        except ValueError:
                            try:
                                float(value)
                                data_types[i] = 'REAL'
                            except ValueError:
                                pass  # Value remains as TEXT

            self.update_channels_table('moas_channels', headers, data_types)
            
            with open(csv_file, 'r') as file:
                csv_reader = csv.DictReader(file)
                for row in csv_reader:
                    query = f'INSERT INTO moas_channels (config_id'
                    placeholder = '(?'
                    values = (config_id,)
                    for column_name, value in row.items():
                        query += f', {column_name}'
                        placeholder += ', ?'
                        values += (value,)
                    query += ') VALUES '
                    placeholder += ');'
                    query += placeholder
                    self.cursor.execute(query,values)
        self.conn.commit()

    def import_foas_configuration(self, csv_file, tag):
        """Import a FOAS CSV into the database.

        Expects filenames like 'FOAS_<version>.csv'. Creates `foas_versions` and
        `foas_channels` entries similar to MOAS importer.
        """
        version = os.path.splitext(os.path.basename(csv_file))[0]
        if version.startswith('FOAS_'):
            version = version[5:]
        else:
            raise ValueError("Invalid FOAS filename")

        # Check if version tag already exists
        self.cursor.execute('SELECT version FROM foas_versions WHERE version = ?', (version,))
        existing_version = self.cursor.fetchone()

        if not existing_version:
            self.cursor.execute('INSERT INTO foas_versions (version,tag) VALUES (?,?)', (version,tag))
            config_id = self.cursor.lastrowid

            with open(csv_file, 'r') as file:
                csv_reader = csv.reader(file)
                headers = next(csv_reader)
                data_types = []
                for _ in headers:
                    data_types.append('TEXT')
                for row in csv_reader:
                    for i, value in enumerate(row):
                        try:
                            int(value)
                            data_types[i] = 'INTEGER'
                        except ValueError:
                            try:
                                float(value)
                                data_types[i] = 'REAL'
                            except ValueError:
                                pass

            self.update_channels_table('foas_channels', headers, data_types)

            with open(csv_file, 'r') as file:
                csv_reader = csv.DictReader(file)
                for row in csv_reader:
                    query = f'INSERT INTO foas_channels (config_id'
                    placeholder = '(?'
                    values = (config_id,)
                    for column_name, value in row.items():
                        query += f', {column_name}'
                        placeholder += ', ?'
                        values += (value,)
                    query += ') VALUES '
                    placeholder += ');'
                    query += placeholder
                    self.cursor.execute(query,values)
        self.conn.commit()

    def update_active_foas_configuration(self, version):
        self.cursor.execute('UPDATE foas_versions SET is_active = 0')
        self.cursor.execute('UPDATE foas_versions SET is_active = 1 WHERE version = ?', (version,))
        self.conn.commit()

    def get_active_foas_configuration(self):
        self.cursor.execute('SELECT version FROM foas_versions WHERE is_active = 1')
        current_config = self.cursor.fetchone()
        if current_config:
            return current_config[0]
        else:
            return None

    # Function to print configurations as a table
    def print_configurations_table(self, configurations):
        if not configurations:
            print("No configurations found.")
            return
        
        headers = [description[0] for description in self.cursor.description]
        table = PrettyTable(headers)
        for config in configurations:
            table.add_row(config)
        print(table)

    # Function to query configurations by tag
    def get_configurations_by_version(self, version):
        self.cursor.execute('''
            SELECT moas_versions.version, moas_channels.*
            FROM moas_versions
            JOIN Channels ON moas_versions.config_id = moas_channels.config_id
            WHERE moas_versions.version = ?
        ''', (version,))
        configurations = self.cursor.fetchall()
        self.print_configurations_table(configurations)

    def update_active_configuration(self, version):
        self.cursor.execute('UPDATE moas_versions SET is_active = 0')
        self.cursor.execute('UPDATE moas_versions SET is_active = 1 WHERE version = ?', (version,))
        self.conn.commit()

    def get_active_configuration(self):
        self.cursor.execute('SELECT version FROM moas_versions WHERE is_active = 1')
        current_config = self.cursor.fetchone()
        if current_config:
            return current_config[0]
        else:
            return None  # Return None if no currently used configuration found