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

# In[]:

assert not any(mt.errors for cf in cha_files for mt in cf.main_tiers)

# # Step 2
# 
# Manually check the ones where the number of annotated words is different from the number of the transcriptions.

# In[60]:

from collections import defaultdict

main_tiers = defaultdict(list)
for cf in cha_files:
    for mt in cf.main_tiers:
        if mt.contents == ('bug &=n_n_CHI_0x227315 &CV &=w9_66 . \x151057910_1060130\x15\n',):
            continue
        main_tiers[mt.update_pho(SPEAKER_CODE)].append((cf, mt))


# In[47]:


for status, mts in main_tiers.items():
    print(status, len(mts))


# In[55]:


def print_tiers_with_status(str_status):
    for cf, mt in main_tiers[str_status]:
        print(cf.path.name)
        print(mt)
        print('Annotated words: ', *mt.words_uttered_by[SPEAKER_CODE])
        print('\n')


def print_tiers_with_status_to_file(str_status, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        with redirect_stdout(f):
            print_tiers_with_status(str_status)


# In[61]:


print_tiers_with_status_to_file(
    str_status='error: more transcriptions than there are words',
    path='reports/cha/too_many_transcriptions.txt')


# In[58]:


print_tiers_with_status_to_file(
    str_status='error: fewer transcriptions than there are words, order unknown, sort manually',
    path='reports/cha/too_few_transcriptions.txt')


# In[59]:


print_tiers_with_status('###\'s added, needs transcription')


# In[63]:
# Check that the file can be compiled back form the parsed version.

for cf in cha_files:
    if not cf.no_changes():
        raise ValueError


# n words, m transcriptions
# - no pho - add pho with n '###'
# - m == n - nevermind
# - m < n  - add (n-m) '###', extract to a separate list for sorting, unless all '###'
# - m > n  - another list
