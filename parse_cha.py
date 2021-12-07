from pathlib import Path
from collections import defaultdict

from IPython import get_ipython

get_ipython().run_line_magic('load_ext', 'autoreload')
get_ipython().run_line_magic('autoreload', '1')
get_ipython().run_line_magic('aimport', 'cha')
from cha import CHAFile


SPEAKER_CODE = 'CHI'


# In[]:
# # Find all the chas
seedlings_path = Path('/Volumes/pn-opus/Seedlings')
assert seedlings_path.exists()

cha_file_path_list = seedlings_path.joinpath('Scripts_and_Apps/Github/seedlings/path_files/cha_sparse_code_paths.txt')
assert cha_file_path_list.exists()

with cha_file_path_list.open('r', encoding='utf-8') as f:
    cha_paths = list(map(lambda line: Path(line.rstrip()), f))


# In[]:
# # Load an parse

cha_files = [CHAFile(cha_path) for cha_path in cha_paths]

for i, cha_file in enumerate(cha_files):
    end = '\n' if i % 20 == 19 else ' '
    print(f'{i:03}', end=end)
    
    cha_file.process_for_phonetic_transcription(SPEAKER_CODE)


# Check for parsing errors
first_lines_to_skip = (
    'penguin &=n_y_CHI_0x352e93 penguin &=n_y_CHI_0x366d19 penguin\n',
    'oranges &=d_y_MOT_0x1d8f75 apples &=d_n_MOT_0x4945d6 oranges\n',
    'apple &=n_y_CHI_0x5f42b9 apple &=n_y_CHI_0xb1a1bb apple &=n_y_CHI\n')

assert not any(mt.errors and mt.contents[0] not in first_lines_to_skip for cf in cha_files for mt in cf.main_tiers)

# In[]
# # Check that the files can be reconstructed without changes before introducing any
for cf in cha_files:
    if not cf.no_changes():
        raise ValueError


# In[]
# # Add pho tier or '###' and check for transcription errors (too few, too many, etc.)
main_tiers = defaultdict(list)
for cf in cha_files:
    for mt in cf.main_tiers:
        # Skip main tiers with a missing annotid
        if mt.contents[0] in first_lines_to_skip:
            continue
        main_tiers[mt.update_pho(SPEAKER_CODE)].append((cf, mt))

assert not any(status.startswith('error') for status in main_tiers)

# In[]
# # Write the results
test_dir = Path.home() / 'blab' / 'annotated_cha' / 'annotated_cha'
assert test_dir.exists()
for cf in cha_files:
    output_path = test_dir / cf.path.name
    cf.write(path=output_path)
