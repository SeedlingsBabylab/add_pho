import datetime
from pathlib import Path
import os
import re

import pandas as pd
import numpy as np


from opf import OPFFile, OPFDataFrame


PHO_PREFIX = r'^%pho:?(?:&|\s+)'


def collect_all_chi(opf: OPFDataFrame):
    df: pd.DataFrame = opf.df

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
    # empty ('NA' for original columns, '' for the 'pho' column). Sometimes the speaker field value is 'NA\, NEW' or
    # just 'NEW'
    columns_to_keep = ['object', 'id', 'time_start', 'time_end']
    assert df[is_pho].drop(columns_to_keep, axis='columns').isin(['NA', '', 'NA\\, NEW', 'NEW']).all().all()

    chis_with_phos = pd.merge_asof(
        df[is_chi],
        # rename time_end to keep both times for approximate matches
        df[is_pho][columns_to_keep].rename(columns={'time_end': 'time_end_pho'}),
        left_on='time_end',
        right_on='time_end_pho',
        suffixes=('', '_pho'),
        direction='nearest',
        tolerance=pd.Timedelta('0.5s'))

    # Add orphan %pho's if any by merging with all the pho's on annotid
    pho_columns = [column + '_pho' for column in columns_to_keep]
    chis_with_phos = chis_with_phos.merge(
        df[is_pho][columns_to_keep].rename(columns=dict(zip(columns_to_keep, pho_columns))),
        on=pho_columns,
        how='outer'
    )

    return chis_with_phos


def add_flags(chis_with_phos):
    # # Add flags from the table above

    # Is there a pho cell?
    chis_with_phos['is_pho_cell'] = ~chis_with_phos.object_pho.isna()

    # Does it have anything in it?
    # First, check that they all have the same prefix "%pho: "
    assert chis_with_phos.object_pho.str.contains(PHO_PREFIX).all()
    # Is there at least one character after the prefix?
    chis_with_phos['is_pho_cell_filled'] = chis_with_phos.object_pho.str.replace(PHO_PREFIX, '', regex=True).str.len() > 0

    # Is there a pho field
    is_pho_field = 'pho' in chis_with_phos.columns
    chis_with_phos['is_pho_field'] = is_pho_field

    # Does it have anything in it?
    # First, check that they all have the same prefix "%pho"
    assert chis_with_phos.object_pho.str.contains(PHO_PREFIX).all()
    # Is there at least one character after the prefix?
    if is_pho_field:
        chis_with_phos['is_pho_field_filled'] = chis_with_phos.pho.str.replace(PHO_PREFIX, '', regex=True).str.len() > 0
    # If there was no pho field, add a NaN column. This is different from an empty pho field which is an empty string.
    else:
        chis_with_phos['pho'] = np.nan
        chis_with_phos['is_pho_field_filled'] = np.nan

    return chis_with_phos


def _open_db_in_text_editor(path_to_opf):
    """
    Opens and opf file in the default text editor
    May overwirte files, be careful.
    :param path_to_opf: full path
    :return: nothing
    """
    os.system(f'cp {path_to_opf} ~/blab/zhenya/test.opf')
    os.system('unzip -o test.opf')  # -o - overwrite without prompting
    os.system('open db')


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

opf_files = list(map(OPFFile, opf_paths))
opf_df = list(map(OPFDataFrame, opf_files))

all_chis = list(map(collect_all_chi, opf_df))

all_chis_with_flags = list(map(add_flags, all_chis))


# # Find all the orphan phos
orphans = pd.concat(objs=[df[df.object.isna()] for df in all_chis],
                    keys=[opf.path for opf in opf_files],
                    names=['file_path', 'index'])

# Clean and save to a csv
# A random date was added to time for technical reasons, we don't need it anymore
orphans.time_end = orphans.time_end.dt.time
orphans = orphans[['object_pho', 'id_pho', 'time_start_pho', 'time_end_pho']].reset_index(0)

# Save
orphans_output_path = Path('repo') / 'reports' / 'orphan_phos.csv'
orphans_output_path.parent.mkdir(exist_ok=True)
orphans.to_csv(orphans_output_path, index=False)


# Find all the non-unique ids (not one-to-one matches)
def find_duplicates(chis: pd.DataFrame):
    return pd.concat(
        objs=[chis[(chis.duplicated(subset=['id', 'time_start', 'time_end'], keep=False)
                    & ~chis.object.isna())],  # don't count empty rows as duplicates of each other
              chis[(chis.duplicated(subset=['id_pho', 'time_start_pho', 'time_end_pho'], keep=False)
                    & ~chis.object_pho.isna())]],
        keys=['CHIs sharing a %pho', '%phos sharing a CHI'],
    )


duplicates = pd.concat(
    objs=map(find_duplicates, all_chis),
    keys=[opf.path for opf in opfs],
    names=['file_path', 'type of duplicate', 'index'])

duplicates_output_path = Path('repo') / 'reports' / 'duplicates.csv'
duplicates_output_path.parent.mkdir(exist_ok=True)
duplicates.reset_index([0, 1]).to_csv(duplicates_output_path, index=False)


# Pivot tables
def make_pivot(chis):
    return (chis
            .groupby(['is_pho_cell', 'is_pho_cell_filled', 'is_pho_field', 'is_pho_field_filled'], dropna=False)
            .size()
            .to_frame('size')
            .reset_index())


pivots = pd.concat(
    objs=map(make_pivot, all_chis),
    keys=[opf.path for opf in opfs],
    names=['file_path', 'index']
)

grand_pivot = (pivots
               .groupby(['is_pho_cell', 'is_pho_cell_filled', 'is_pho_field', 'is_pho_field_filled'], dropna=False)
               .sum()
               .reset_index())



