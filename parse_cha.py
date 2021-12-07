#!/usr/bin/env python
# coding: utf-8

# In[0]
from contextlib import redirect_stdout

from IPython import get_ipython

get_ipython().run_line_magic('load_ext', 'autoreload')
get_ipython().run_line_magic('autoreload', '1')
get_ipython().run_line_magic('aimport', 'cha')
get_ipython().run_line_magic('aimport', 'cha_re')
from cha import CHAFile

# In[]
from pathlib import Path



# In[2]:


SPEAKER_CODE = 'CHI'


# In[3]:

seedlings_path = Path('/Volumes/pn-opus/Seedlings')
assert seedlings_path.exists()

cha_file_path_list = seedlings_path.joinpath('Scripts_and_Apps/Github/seedlings/path_files/cha_sparse_code_paths.txt')
assert cha_file_path_list.exists()

with cha_file_path_list.open('r', encoding='utf-8') as f:
    cha_paths = list(map(lambda line: Path(line.rstrip()), f))


# # Load an parse
# In[4]:

cha_files = [CHAFile(cha_path) for cha_path in cha_paths]

for i, cha_file in enumerate(cha_files):
    end = '\n' if i % 20 == 19 else ' '
    print(f'{i:03}', end=end)
    
    cha_file.process_for_phonetic_transcription(SPEAKER_CODE)


# # Step 1, check for errors

# Three main tiers have been updated and now have annotid missing. We will skip them here.
first_lines_to_skip = (
    'penguin &=n_y_CHI_0x352e93 penguin &=n_y_CHI_0x366d19 penguin\n',
    'oranges &=d_y_MOT_0x1d8f75 apples &=d_n_MOT_0x4945d6 oranges\n',
    'apple &=n_y_CHI_0x5f42b9 apple &=n_y_CHI_0xb1a1bb apple &=n_y_CHI\n')

assert not any(mt.errors and mt.contents[0] not in first_lines_to_skip for cf in cha_files for mt in cf.main_tiers)

# # Step 2
# 
# Manually check the ones where the number of annotated words is different from the number of the transcriptions.

# In[60]:

from collections import defaultdict

main_tiers = defaultdict(list)
for cf in cha_files:
    for mt in cf.main_tiers:
        # Skip main tiers with a missing annotid
        if mt.contents[0] in first_lines_to_skip:
            continue
        main_tiers[mt.update_pho(SPEAKER_CODE)].append((cf, mt))

for status, mts in main_tiers.items():
    print(status, len(mts))

# After manual edits, the only error should be "error: CHI not in annotation"
assert not any(status.startswith('error') and status != 'error: CHI not in annotation'
               for status
               in main_tiers)


for cf in cha_files:
    if not cf.no_changes():
        raise ValueError

