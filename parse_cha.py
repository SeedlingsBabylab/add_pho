from pathlib import Path
from collections import defaultdict

from cha import CHAFile, TRANSCRIPTION_LABEL


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
    assert cf.no_changes()


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
# # No new changes
# This script has already been run, no new changes should have been introduced
for cf in cha_files:
    assert cf.no_changes(), 'We\'ve already edited/added pho subtiers so no changes should have been introduced'

# In[]
# # Write the results
# for cf in cha_files:
#     cf.write(overwrite_original=True)


# In[]
# # Output a list of words that need transcription
to_transcribe = list()
for cf in cha_files:
    for mt in cf.main_tiers:
        if SPEAKER_CODE in mt.words_uttered_by:
            for word, annotid, transcription in zip(mt.words_uttered_by[SPEAKER_CODE],
                                                    mt.annotid_of_words_uttered_by[SPEAKER_CODE],
                                                    mt.transcriptions):
                if transcription == '###':
                    to_transcribe.append((cf.path.absolute(),
                                          word,
                                          annotid,
                                          transcription))

to_transcribe_path = Path('reports/cha/to_transcribe.csv')
to_transcribe_path.parent.mkdir(parents=True, exist_ok=True)
import pandas as pd
to_transribe_df = pd.DataFrame(
    columns=('file_path', 'word', 'annotid', 'transcription'),
    data=to_transcribe)
to_transribe_df.to_csv('reports/cha/to_transcribe.csv', index=False)
