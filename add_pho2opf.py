from zipfile import ZipFile, BadZipfile
import re, sys, pdb, os, pdb, argparse




code_reg = re.compile(r'([0-9]{2}:[0-9]{2}:[0-9]{2}:[0-9]{3}),\((.*,[a-z],[a-z],([A-Z]{3}),.*)\)')

def get_args():
    parser = argparse.ArgumentParser(description='Add pho cells to the opf file. The script moves \"old\" style pho annotations with a pho cell. If the script was run on a given file before, it will not run again.')
    parser.add_argument('input_file', help='The path to the input opf file.')
    parser.add_argument('-o', '--output-path', help='Path of the output file. If no output is specified, the input opf path is used (so the input file is modified)')
    return parser.parse_args()

# Decided to turn opf file into a class :)
class opf_file:

    def __init__(self, path):
        self.path = path

        try:
            with ZipFile(path, 'r') as zpf:
                namelist = zpf.namelist()
                if 'db' in namelist:
                    zpf.extractall()
                    self.namelist = zpf.namelist()
                    self.in_lines = zpf.open('db').readlines()
                    os.remove('db')


                else:
                    print 'db file is not included in the opf! Exiting'
                    exit()

        except BadZipfile as e:
            print 'The supplied file does not look like an opf file (since it is not a zip file)?'
            print e

    def output(self, path=None):
        if path == None:
            path = self.path
        try:
            with ZipFile(path, 'w') as zpf:
                zpf.writestr('db', ''.join(self.in_lines))
                for item in self.namelist:
                    if item != 'db':
                        zpf.write(item)
                        os.remove(item)

        except BadZipfile as e:
            print 'The supplied file does not look like an opf file (since it is not a zip file)?'
            print e
            

# Check for the pho code in the header, if not there, add it!
# The function does not return anything, BUT modifies the input!
# Which is a list of lines from the db file!
def check_pho_code(in_lines):
    def add_pho_code(line):
        return line.strip() + ',pho|NOMINAL\n'

    for i, line in enumerate(in_lines):

        # Check if this is the header line
        if 'labeled_object' in line:
            if 'pho' in line:
                print('pho code was already added to this file')
                print('skipping the pho code addition')
            else:
                in_lines[i] = add_pho_code(line)
                print('{} replaced with:\n {}'.format(line, in_lines[i]))

def process(in_lines):
    def add_pho_code(pho_line, line):
        pat = re.compile('\((.*)\)')
        pho = re.compile('(%pho:[^,]*),')
        m = pat.search(line).group(1)
        ph = pho.search(pho_line)
        return line.replace(m, m + ',' + ph.group(1))

    i = 0
    while i < len(in_lines):
        line = in_lines[i]
        m = code_reg.search(line)
        # If a pho code was already added, we skip!
        if m and 'CHI' in m.groups() and '%pho' not in line:
            j = i + 1
            while j < i + 5:
                if '%pho' in in_lines[j]:
                    # group 2 contains the actual annotations.
                    # If the number of codes is more than 5, then don't add anything.
                    annots = m.group(2).split(',')
                    if len(annots) >= 6:
                        break
                    in_lines[i] = add_pho_code(in_lines[j], line)
                    print('{} replaced with:\n{} The line below was deleted:\n{}'.format(line, in_lines[i], in_lines[j]))
                    del(in_lines[j])
                    i = j
                    break
                j += 1
            else:
                print('No pho cell could be found for line:\n{}'.format(line))
        else:
            # Bad code but I want visual confirmation of addition for now.
            if m and 'CHI' in m.groups():
                print(line)

        i += 1

if __name__ == "__main__":
    args = get_args()
    myopf = opf_file(args.input_file)
    check_pho_code(myopf.in_lines)
    process(myopf.in_lines)
    myopf.output(args.output_path)
