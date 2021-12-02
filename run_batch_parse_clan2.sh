script=/Volumes/pn-opus/Seedlings/Scripts_and_Apps/Github/seedlings/parse_clan2/batch_parse_clan2.py
cha_files_master=/Volumes/pn-opus/Seedlings/Scripts_and_Apps/Github/seedlings/annotated_cha/annotated_cha/
processed_files=/Users/ek221/blab/02_fix-pho/repo

cha_files=$cha_files_master
python $script $cha_files  $processed_files
