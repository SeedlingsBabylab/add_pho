speaker = '(?P<speaker>CHI|MOT|FAT|SIS)'
annotation = fr'(?P<word>[\w+]+) &=[s|d|n|y|i]_[n|y]_{speaker}_0x[a-z0-9]{{6}}'
annotations = fr'(?P<annotations>(?:{annotation} +)*)'

lena_annotation = r'(?:0|&=(?:w\d+(?:_\d+)?|vocalization|crying|vfx))'
timestamp = r'\x15\d+_\d+\x15'
maybe_zero = r'(?:0 )?'
maybe_dot = r'(?:\. )?'
other = fr'(?:{lena_annotation} +)?{maybe_zero}{maybe_dot}{timestamp}'

main_tier_content_pattern = fr'{annotations}{other}$'
# used to identify main tier lines manually split over multiple lines
ends_with_a_timestamp = fr'^.*{timestamp}$'

transcription_pattern = r"^[a-zA-Z?&'36:.+]+$"
