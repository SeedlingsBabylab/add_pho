import datetime
from pathlib import Path
from zipfile import ZipFile
import os
import re

import pandas as pd
import numpy as np


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
            # Commas within filed values are escaped by a backslash - we don't want to split on those
            values = values[:2] + re.split(r'(?<!\\),', values[2].strip('()'))
            return values
        data = list(map(row_to_values, self.db[2:]))

        # Bind
        df = pd.DataFrame(columns=field_names, data=data)

        # Format time
        df['time_start'] = pd.to_datetime(df.time_start, format='%H:%M:%S:%f').dt.time
        df['time_end'] = pd.to_datetime(df.time_end, format='%H:%M:%S:%f').dt.time

        return df


def collect_all_chi(opf: OPFFile):
    PHO_PREFIX = r'^%pho:?(?:&|\s+)'

    df: pd.DataFrame = opf.to_pandas_df()

    # Sort by time_end
    df.sort_values(by='time_end', inplace=True)

    # Find child utterances
    is_chi = df.speaker == 'CHI'

    # Find phonetic transcriptions in separate cells
    is_pho = df.object.str.contains(PHO_PREFIX)

    # # Merge
    # We will first need to convert time_end to datetime
    random_date = str(datetime.datetime.strptime('1988-11-11', '%Y-%m-%d').date())
    df['time_end'] = pd.to_datetime(random_date + " " + df.time_end.astype(str))

    # The only fields in %pho rows we care about are time_start, time_end, annotid and object. The other ones should be
    # empty ('NA' for original columns, '' for the 'pho' column). Let's check that.
    columns_to_keep = ['object', 'id', 'time_start', 'time_end']
    df[is_pho].drop(columns_to_keep, axis='columns').isin(['NA', '']).all().all()

    chi_with_pho = pd.merge_asof(
        df[is_chi],
        # rename time_end to keep both times for approximate matches
        df[is_pho][columns_to_keep].rename(columns={'time_end': 'time_end_pho'}),
        left_on='time_end',
        right_on='time_end_pho',
        suffixes=('', '_pho'),
        direction='nearest',
        tolerance=pd.Timedelta('0.5s'))

    # Add orphan %pho's if any by merging with all the pho's on annotid
    chi_with_pho = chi_with_pho.merge(
        df[is_pho][['id', 'object']].rename(columns={'id': 'id_pho', 'object': 'object_pho'}),
        on=['id_pho', 'object_pho'],
        how='right'
    )

    # # Add flags from the table above

    # Is there a pho cell?
    chi_with_pho['is_pho_cell'] = ~chi_with_pho.object_pho.isna()

    # Does it have anything in it?
    # First, check that they all have the same prefix "%pho: "
    assert chi_with_pho.object_pho.str.contains(PHO_PREFIX).all()
    # Is there at least one character after the prefix?
    chi_with_pho['is_pho_cell_filled'] = chi_with_pho.object_pho.str.replace(PHO_PREFIX, '', regex=True).str.len() > 0

    # Is there a pho field
    is_pho_field = 'pho' in chi_with_pho.columns
    chi_with_pho['is_pho_field'] = is_pho_field

    # Does it have anything in it?
    # First, check that they all have the same prefix "%pho"
    assert chi_with_pho.object_pho.str.contains(PHO_PREFIX).all()
    # Is there at least one character after the prefix?
    if is_pho_field:
        chi_with_pho['is_pho_field_filled'] = chi_with_pho.pho.str.replace(PHO_PREFIX, '', regex=True).str.len() > 0
    # If there was no pho field, add a NaN column. This is different from an empty pho field which is an empty string.
    else:
        chi_with_pho['pho'] = np.nan
        chi_with_pho['is_pho_field_filled'] = np.nan

    return chi_with_pho


opf_path = Path('01_17_sparse_code.opf')
opf = OPFFile(opf_path)
chi_with_pho = collect_all_chi(opf)

# Make a pivot table
print(chi_with_pho
      .groupby(['is_pho_cell', 'is_pho_cell_filled', 'is_pho_field', 'is_pho_field_filled'])
      .size())


# # Find all opfs

# Locate Subject_Files
pn_opus_dir = Path(os.environ.get('pn_opus') or '/Volumes/pn-opus')
assert pn_opus_dir.exists(), f'Mount pn-opus or set env var "pn_opus" to actual path instead of {pn_opus_dir}'
subject_files_dir = pn_opus_dir / 'Seedlings' / 'Subject_Files'


# Function to find files somewhat efficiently
def find_matching(list_of_roots, pattern):
    # Recursion stop
    if pattern is None:
        return list_of_roots

    if '/' in pattern:
        this_level, rest_of_the_pattern = pattern.split('/', maxsplit=1)
    else:
        this_level, rest_of_the_pattern = pattern, None

    new_roots = [match
                 for root in list_of_roots
                 for match in filter(lambda x: re.match(this_level, x.name),
                                     root.glob('*'))]

    # list_of_roots = new_roots[:1]
    # pattern = rest_of_the_pattern

    return find_matching(new_roots, rest_of_the_pattern)


# Find all opf files
opf_path = r'\d{2}/\d{2}_\d{2}/Home_Visit/Coding/Video_Annotation/\d{2}_\d{2}_sparse_code.opf'

list_of_roots = [subject_files_dir]
pattern = opf_path
opf_paths = find_matching(list_of_roots, pattern)

opfs = list(map(OPFFile, opf_paths))
all_chis = list(map(collect_all_chi, opfs))
# Find all the orphan phos

