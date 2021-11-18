import re
from zipfile import ZipFile

import pandas as pd


class OPFFile(object):
    def __init__(self, path):
        self.path = path
        self.db, self.other = self.load()

    def load(self):
        with ZipFile(self.path, 'r') as zpf:
            assert 'db' in zpf.namelist(), f'The file at {self.path} does not contain "db". Not an OPF file?'

            # Annotations
            with zpf.open('db', 'r') as f:
                db = f.read().splitlines()
            # zpf.open read file in binary mode
            db = [line.decode('utf-8') for line in db]

            # Other components
            other_files = {name: zpf.open(name, 'r').read()
                           for name in zpf.namelist()
                           if name != 'db'}

        return db, other_files


class OPFDataFrame(object):
    def __init__(self, opf_file: OPFFile):
        self.opf_file = opf_file
        self.df = self._opf_to_pandas_df()

    def _opf_to_pandas_df(self):
        # Extract field names
        # There is a single datavyu column "labeled_object" defined in the second line of "db".
        # The format of this line is <column-definition>-<field_definitions>
        field_definitions = self.opf_file.db[1].split('-')[1]
        # Field definitions are comma-separated, each definition has the following format: <field_name>|<field_type>
        field_names = [field_definition.split('|')[0] for field_definition in field_definitions.split(',')]
        # The first two columns contain timestamps
        field_names = ['time_start', 'time_end'] + field_names

        # Extract values
        # Each data row in db is in this format: <time_start>,<time_end>,(<field1>,...,<fieldN>)
        def row_to_values(row):
            values = row.split(',', maxsplit=2)
            # Commas within filed values are escaped by a backslash - we don't want to split on those
            values = values[:2] + re.split(r'(?<!\\),', values[2].strip('()'))
            return values
        data = list(map(row_to_values, self.opf_file.db[2:]))

        # Bind
        df = pd.DataFrame(columns=field_names, data=data)

        # Format time
        df['time_start'] = pd.to_datetime(df.time_start, format='%H:%M:%S:%f').dt.time
        df['time_end'] = pd.to_datetime(df.time_end, format='%H:%M:%S:%f').dt.time

        return df
