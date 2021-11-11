from pathlib import Path
from zipfile import ZipFile

import pandas as pd


class OPFFile(object):
    def __init__(self, path):
        self.path = path
        self.db, self.project = self.load()

    def load(self):
        with ZipFile(self.path, 'r') as zpf:
            assert set(zpf.namelist()) == {'db', 'project'}

            # Annotations
            with zpf.open('db', 'r') as f:
                db = f.read().splitlines()
            # zpf.open read file in binary mode
            db = [line.decode('utf-8') for line in db]

            # Metadata
            with zpf.open('project', 'r') as f:
                project = f.read()

        return db, project

    def to_pandas_df(self):
        # Extract field names
        # There is a single datavyu column "labeled_object" defined in the second line of "db".
        # The format of this line is <column-definition>-<field_definitions>
        field_definitions = self.db[1].split('-')[1]
        # Field definitions are comma-separated, each definition has the following format: <field_name>|<field_type>
        field_names = [field_definition.split('|')[0] for field_definition in field_definitions.split(',')]
        # The first two columns contain timestamps
        field_names = ['time_start', 'time_end'] + field_names

        # Extract values
        # Each data row in db is in this format: <time_start>,<time_end>,(<field1>,...,<fieldN>)
        def row_to_values(row):
            values = row.split(',', maxsplit=2)
            values = values[:2] + values[2].strip('()').split(',')
            return values
        data = list(map(row_to_values, self.db[2:]))

        # Bind
        df = pd.DataFrame(columns=field_names, data=data)

        # Format time
        df['time_start'] = pd.to_datetime(df.time_start, format='%H:%M:%S:%f').dt.time
        df['time_end'] = pd.to_datetime(df.time_end, format='%H:%M:%S:%f').dt.time

        return df


opf_path = Path('01_17_sparse_code.opf')
opf = OPFFile(opf_path)
