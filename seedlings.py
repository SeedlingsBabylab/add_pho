import os
from pathlib import Path
import re

# Locate the 'Seedlings' directory
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
