#!/usr/bin/env python
# coding: utf-8

# In[0]
from IPython import get_ipython

get_ipython().run_line_magic('load_ext', 'autoreload')
get_ipython().run_line_magic('autoreload', '1')
get_ipython().run_line_magic('aimport', 'cha')
get_ipython().run_line_magic('aimport', 'cha_re')
from cha import CHAFile


# In[1]:

from pathlib import Path


# In[2]:


SPEAKER_CODE = 'CHI'


# In[3]:


cha_repo = Path.home() / 'blab' / 'annotated_cha'
cha_paths = list(cha_repo.glob('annotated_cha/*.cha'))


# In[4]:


cha_files = [CHAFile(cha_path) for cha_path in cha_paths]

for i, cha_file in enumerate(cha_files):
    end = '\n' if i % 20 == 19 else ' '
    print(f'{i:03}', end=end)
    
    cha_file.process_for_phonetic_transcription(SPEAKER_CODE)


# # Step 1

# In[16]:


with_errors = list()
for cf in cha_files:
    for mt in cf.main_tiers:
        if mt.errors:
            with_errors.append((cf, mt))
            print(cf.path)
            print(mt)
            for error in mt.errors:
                print(error)
            print()


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


def print_tiers_with_status(status):
    for cf, mt in main_tiers[status]:
        print(cf.path)
        print(mt)
        print('Annotated words: ', *mt.words_uttered_by[SPEAKER_CODE])
        print('\n')


# In[61]:


print_tiers_with_status('error: more transcriptions than there are words')


# In[58]:


print_tiers_with_status('error: fewer transcriptions than there are words, order unknown, sort manually')


# In[59]:


print_tiers_with_status('pho subtier added')


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
