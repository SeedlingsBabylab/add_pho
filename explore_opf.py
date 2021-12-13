import os
from pathlib import Path

import pandas as pd

from opf import OPFFile, OPFDataFrame, DATETIME_FORMAT


PHO_PREFIX = r'^%pho:?(?:&|\s+)'


def collect_all_chi(opf: OPFDataFrame):
    """
    Finds all CHI and %pho cells and establishes their correspondence.
    :param opf: OPFDataFrame object
    :return: opf.df with only the CHI rows and with additional columns corresponding to the pho cell.
    """
    df: pd.DataFrame = opf.df.copy()

    # For the fuzzy merging (time_end of CHI and %pho being approximately equal), we will need time_end to be a numeric
    # (datetime in this case) column and sorted.
    df['time_end'] = pd.to_datetime(df.time_end, format=DATETIME_FORMAT)
    df.sort_values(by='time_end', inplace=True)

    # Find child utterance and pho cells
    is_chi = df.speaker == 'CHI'
    is_pho = df.object.str.contains(PHO_PREFIX)

    # We will only need some columns from the pho cells: time_start, time_end, annotid and object. The other ones should
    # be empty ('NA' for original columns, '' for the 'pho' column). The exception is that sometimes the speaker field
    # value is 'NA\, NEW' or 'NEW' - we can disregard this information.
    columns_to_keep = ['object', 'id', 'time_start', 'time_end']
    assert df[is_pho].drop(columns_to_keep, axis='columns').isin(['NA', '', 'NA\\, NEW', 'NEW']).all().all()

    # # Merge
    chis_with_phos = pd.merge_asof(
        df[is_chi],
        # rename time_end to keep both times for approximate matches
        df[is_pho][columns_to_keep].rename(columns={'time_end': 'time_end_pho'}),
        left_on='time_end',
        right_on='time_end_pho',
        suffixes=('', '_pho'),
        direction='nearest',
        tolerance=pd.Timedelta('0.5s'))

    # Add orphan %pho's - if any - by merging with all the pho's on annotid.
    # By merging on all the pho columns, we won't add any new columns.
    # If multiple CHI cells were found to correspond to a single pho cell, this will result in duplicate columns. Same
    # will happen if there identical pho rows.
    pho_columns = [column + '_pho' for column in columns_to_keep]
    chis_with_phos = chis_with_phos.merge(
        df[is_pho][columns_to_keep].rename(columns=dict(zip(columns_to_keep, pho_columns))),
        on=pho_columns,
        how='outer'
    )

    return chis_with_phos


# # Main

# locate all the opf files
seedlings_path = Path('/Volumes/pn-opus/Seedlings')
assert seedlings_path.exists()

opf_file_path_list = seedlings_path.joinpath('Scripts_and_Apps/Github/seedlings/path_files/opf_paths.txt')
assert opf_file_path_list.exists()

with opf_file_path_list.open('r', encoding='utf-8') as f:
    opf_paths = [Path(path.rstrip()) for path in f]


# Read and convert to dataframes
opf_files = list(map(OPFFile, opf_paths))
for of in opf_files:
    of.load()
opf_dfs = list(map(OPFDataFrame, opf_files))


problems = [df for df in opf_dfs if not df.can_be_reversed()]
assert len(problems) == 0


# Find all the CHIs, the corresponding phos, and classify them
all_chis_with_phos = pd.concat(
    objs=map(collect_all_chi, opf_dfs),
    keys=[opf.path for opf in opf_files],
    names=['file_path', 'index']
).reset_index(0)


# # Find all the orphan phos
orphans = all_chis_with_phos[all_chis_with_phos.object.isna()].copy()

# Clean
# A random date was added to time for technical reasons, we don't need it anymore
orphans.time_end_pho = orphans.time_end_pho.dt.time
orphans = orphans[['file_path', 'object_pho', 'id_pho', 'time_start_pho', 'time_end_pho']]


# Save
orphans_output_path = Path('repo') / 'reports' / 'orphan_phos.csv'
orphans_output_path.parent.mkdir(exist_ok=True)
orphans.to_csv(orphans_output_path, index=False)


# Find all the non-unique ids (not one-to-one matches)

# These column combinations are supposed to be unique
unique_chi_columns = ['file_path', 'id', 'time_start', 'time_end']
unique_pho_columns = ['file_path', 'id_pho', 'time_start_pho', 'time_end_pho']

duplicates = pd.concat(
        objs=[all_chis_with_phos[(
                all_chis_with_phos.duplicated(subset=unique_chi_columns, keep=False)
                & ~all_chis_with_phos.object.isna())],  # don't count empty rows as duplicates of each other
              all_chis_with_phos[(
                all_chis_with_phos.duplicated(subset=unique_pho_columns, keep=False)
                & ~all_chis_with_phos.object_pho.isna())]],
        keys=['CHIs sharing a %pho', '%phos sharing a CHI'],
        names=['duplicate_type', 'index']
    ).reset_index(0)

duplicates_output_path = Path('repo') / 'reports' / 'duplicates.csv'
duplicates_output_path.parent.mkdir(exist_ok=True)
duplicates.to_csv(duplicates_output_path, index=False)


# Classify based on pho field/cell presence and the transcription actually being there
def add_flags(chis_with_phos):
    """
    Adds binary columns 'is_pho_cell', 'is_pho_cell_filled', 'is_pho_field', 'pho', 'is_pho_field_filled'
    :param chis_with_phos: output of collect_all_chi
    :return: chis_with_phos with four additional columns.
    """

    # Is there a pho cell?
    chis_with_phos['is_pho_cell'] = ~chis_with_phos.object_pho.isna()

    # Does it have anything in it?
    # First, check that they all have the same prefix "%pho: " (all() does not care about NaNs)
    assert chis_with_phos.object_pho.str.contains(PHO_PREFIX).all()
    # Is there at least one character after the prefix?
    chis_with_phos['is_pho_cell_filled'] = (
        (chis_with_phos.object_pho
         # Remove the prefix
         .str.replace(PHO_PREFIX, '', regex=True)
         # Is there anything left?
         .str.len() > 0)
        # We want NaN, not False when there was no pho field
        .where(chis_with_phos.is_pho_cell)
    )

    # Is there a pho field?
    # If there was, and it was empty, then it would equal to '' now; if there wasn't, it would now be NaN.
    chis_with_phos['is_pho_field'] = ~chis_with_phos.pho.isna()

    # Does it have anything in it?
    # First, check that they all have the same prefix "%pho: "
    assert chis_with_phos.object_pho.str.contains(PHO_PREFIX).all()
    # Is there at least one character after the prefix?
    chis_with_phos['is_pho_field_filled'] = (
        (chis_with_phos.pho
         # Remove the prefix
         .str.replace(PHO_PREFIX, '', regex=True)
         # Is there anything left?
         .str.len() > 0)
        # We want NaN, not False when there was no pho field
        .where(chis_with_phos.is_pho_field))

    return chis_with_phos


all_chis_with_phos_with_flags = add_flags(all_chis_with_phos)


# Inconsistent transcriptions
# These are annotations that have both the pho cell and the pho column filled
inconsistent_ones = all_chis_with_phos_with_flags[
    all_chis_with_phos_with_flags.is_pho_cell_filled
    & all_chis_with_phos_with_flags.is_pho_field_filled]

inconsistent_output_path = Path('repo') / 'reports' / 'inconsistent_ones.csv'
inconsistent_output_path.parent.mkdir(exist_ok=True)
inconsistent_ones.to_csv(inconsistent_output_path, index=False)


# Make summary tables
def make_pivot(chis):
    return (chis
            .groupby(['is_pho_cell', 'is_pho_cell_filled', 'is_pho_field', 'is_pho_field_filled'], dropna=False)
            .size()
            .to_frame('size')
            .reset_index())


make_pivot(all_chis_with_phos_with_flags)


# Filter odd ones


full = all_chis_with_phos_with_flags
is_odd = (full.id_pho.isin(orphans.id_pho) |
          full.id.isin(duplicates.id) | full.id_pho.isin(duplicates.id_pho) |
          full.id.isin(inconsistent_ones.id))

# The remaining duplicates are not really duplicates, they are just two utterance and then one pho cell.
# The timestamp of the pho cell corresponds exactly to the timestamp of the second CHI cell.
is_odd = is_odd & ~full.id.isin(duplicates[duplicates.time_end == duplicates.time_end_pho].id)


make_pivot(all_chis_with_phos_with_flags[~is_odd])

# Add the pho field
no_pho_field_paths = full[~is_odd & ~full.is_pho_field].file_path.unique()
no_pho_field_dfs = [opf_df for opf_df in opf_dfs if opf_df.opf_file.path in no_pho_field_paths]
assert len(no_pho_field_paths) == len(no_pho_field_dfs)
assert not any('pho' in opf_df.df.columns for opf_df in no_pho_field_dfs)

# Should pass now that we have added the pho field already
assert no_pho_field_paths.size == 0

backup_dir = seedlings_path / 'Compiled_Data/annotated_opf/annotated_opf'
assert backup_dir.exists()

for opf_df in no_pho_field_dfs:
    if 'pho' in opf_df.column_definitions or 'pho' in opf_df.df.columns:
        raise ValueError('pho is already a field')

    opf_df.column_definitions += ',pho|NOMINAL'
    opf_df.df['pho'] = ''

    opf_df.opf_file.db = str(opf_df)

    # Write to backup first, commit changes
    output_path = backup_dir / opf_df.opf_file.path.stem
    opf_df.opf_file.write(path=output_path, unzipped=True)


# os.chdir(backup_dir.parent)
# os.system('git commit -m "add pho field to all"')


# Move the transcription
is_pho_in_cell = (~is_odd & full.is_pho_cell & full.is_pho_cell & full.is_pho_field &
                  full.is_pho_field_filled.isin((False, float('nan'))))


for path, sub_df in full[is_pho_in_cell].groupby('file_path'):
    opf_df = next(opf_df for opf_df in opf_dfs if opf_df.opf_file.path == path)

    # Remember column order so that we can put the id column back in the end
    original_column_order = opf_df.df.columns.copy()
    opf_df.df.set_index('id', inplace=True)

    # update the pho field
    for _, row in sub_df.iterrows():
        opf_df.df.at[row.id, 'pho'] = row.object_pho

    # drop pho cells
    opf_df.df.drop(index=sub_df.id_pho.to_list(), inplace=True)

    # restore the index column
    opf_df.df.reset_index(inplace=True)
    opf_df.df = opf_df.df[original_column_order]

    # compile and update db
    opf_df.opf_file.db = str(opf_df)

    # Write to backup
    output_path = backup_dir / opf_df.opf_file.path.stem
    opf_df.opf_file.write(path=output_path, unzipped=True)

assert is_pho_in_cell.sum() == 0
# If stopped here, check the backup repo and commit before proceeding

if is_pho_in_cell.sum() > 0:
    # Overwrite the original files
    for path, sub_df in full[is_pho_in_cell].groupby('file_path'):
        opf_df = next(opf_df for opf_df in opf_dfs if opf_df.opf_file.path == path)
        opf_df.opf_file.write(overwrite_original=True)

    opf_backup_script = seedlings_path / 'Scripts_and_Apps/Github/seedlings/path_files/cp_all_opf.sh'
    os.system(f'bash {opf_backup_script} {opf_file_path_list} {backup_dir}')

    cwd = os.getcwd()
    try:
        os.chdir(backup_dir)
        os.system('git status')
    finally:
        os.chdir(cwd)

    # check that nothing has changed in the backup


# # # Multi-word-utterances and first words
# # Those also have pho cells associated with them
# for opf_df in opf_dfs:
#     is_pho = opf_df.df.object.str.contains(PHO_PREFIX)
#     if is_pho.sum() == 0:
#         continue
#
#     pho_indices_to_drop = list()
#     for index, row in opf_df.df[is_pho].iterrows():
#         previous_object = opf_df.df.loc[index - 1].object
#         if (previous_object.startswith('%com: first word') or
#                 previous_object.startswith('%com: mwu')):
#             # copy the transcription from the pho cell
#             opf_df.df.loc[index - 1].pho = row.object
#             pho_indices_to_drop.append(index)
#
#     if pho_indices_to_drop:
#         opf_df.df.drop(index=pho_indices_to_drop, inplace=True)
#         opf_df.opf_file.db = str(opf_df)
#         output_path = backup_dir / opf_df.opf_file.path.stem
#         opf_df.opf_file.write(path=output_path, unzipped=True)
#
# # Stop execution here so that we don't proceed until manually checking and committing the backup
# 1/0

# Update the original files, once checked and committed the backukp
for opf_df in opf_dfs:
    opf_df.opf_file.write(overwrite_original=True)

# Run the backup script
opf_backup_script = seedlings_path / 'Scripts_and_Apps/Github/seedlings/path_files/cp_all_opf.sh'
os.system(f'bash {opf_backup_script} {opf_file_path_list} {backup_dir}')

cwd = os.getcwd()
try:
    os.chdir(backup_dir)
    os.system('git status')
finally:
    os.chdir(cwd)
