## batch.sh

By supplying a path file to the batch shell script, you can modify 
opf files in bulk. The script is run like this:

./batch.sh paths_to_opf_files.txt

The errors, if there are any, will be printed to stdout.

**NOTE:** The batch script uses gnu parallel to speed things up. It
currently does not support sequential, so right your own shell script
for that. 


### add_pho2cha.py

usage: add_pho2cha.py [-h] [--output_path OUTPUT_PATH] input_file

Add pho tiers for each child utterance.

positional arguments:
  input_file            The cha/opf file to which pho lines will be added.

optional arguments:
  -h, --help            show this help message and exit
  --output_path OUTPUT_PATH
                        Path of the output file, which is the updated cha
                        file, with pho lines added.

### add_pho2opf.py

usage: add_pho2opf.py [-h] [-o OUTPUT_PATH] input_file

Add pho cells to the opf file. The script moves "old" style pho annotations
with a pho cell. If the script was run on a given file before, it will not run
again.

positional arguments:
  input_file            The path to the input opf file.

optional arguments:
  -h, --help            show this help message and exit
  -o OUTPUT_PATH, --output-path OUTPUT_PATH
                        Path of the output file. If no output is specified,
                        the input opf path is used (so the input file is
                        modified)
