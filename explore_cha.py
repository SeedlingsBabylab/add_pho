from seedlings import find_matching, subject_files_dir

# ## Locate all cha files
cha_path_pattern = r'\d{2}/\d{2}_\d{2}/Home_Visit/Coding/Audio_Annotation/\d{2}_\d{2}_sparse_code.cha'
cha_paths = find_matching(list_of_roots=[subject_files_dir], pattern=cha_path_pattern)
