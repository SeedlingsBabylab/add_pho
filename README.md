This code adds/edits placeholders for phonetic transcriptions to annotations (CHA/OPF).
The code intentionally breaks if there are any formatting or other inconsistencies.
If there are any errors, run in interactive mode to investigate.

# CHA files

Run 
```ipython -i add_pho_to_cha/update_pho_in_cha.py```

It will create/update `add_pho_to_cha/to_transcribe.csv`.

The cha-editing part has already been done and is now commented out.
If any new changes are necessary, the script will throw an assertion error since there should be no new changes.
If this happens, and you want the script to update the cha files accordingly:
- run the updating code by hand (see `# Write the results` in the script),
- backup the updated cha files,
- re-run the script - there should be no errors, there might be new words to transcribe.

# Previous version of the code

Previous version can be found under `archive` together with the corresponding README.
