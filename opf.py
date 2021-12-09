import re
import os
from zipfile import ZipFile
import tempfile

import pandas as pd


class OPFFile(object):
    SKIP_PREFIXES = ('.DS_Store', '__MACOSX/')

    def __init__(self, path):
        self.path = path
        self.loaded = False
        self.db = None
        self.other_components = None
        self.filenames_in_archive = None
        self.load()

    def load(self):
        if self.path.is_dir():
            raise NotImplementedError('Reading unarchived version from a folder is not yet implemented')

        with ZipFile(self.path, 'r') as opf_zipped:
            assert 'db' in opf_zipped.namelist(), f'The file at {self.path} does not contain "db". Not an OPF file?'

            # Annotations
            with opf_zipped.open('db', 'r') as db_zipped:
                # ZipFile.open reads files in the binary mode
                db = db_zipped.read().decode('utf-8')

            filenames_in_archive = opf_zipped.namelist()

            # Skip macos-specific hidden files
            filenames_in_archive = [fn for fn in filenames_in_archive
                                    if not any(fn.startswith(prefix) for prefix in self.SKIP_PREFIXES)]

            other_components = {
                name: opf_zipped.open(name, 'r').read()
                for name in filenames_in_archive
                if name != 'db'}

            self.db = db
            self.filenames_in_archive = filenames_in_archive
            self.other_components = other_components
            self.loaded = True

    def read_in_editor(self):
        zf = ZipFile(self.path)
        tempdir = tempfile.mkdtemp()
        zf.extractall(tempdir)
        db_path = os.path.join(tempdir, 'db')
        os.system(f'open {db_path}')


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
