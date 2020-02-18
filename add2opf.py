from zipfile import ZipFile, BadZipfile
import re, sys, pdb




code_reg = re.compile(r'\(.*,[a-z],[a-z],([A-Z]{3}),.*\)')

# Decided to turn opf file into a class :)
class opf_file:

    def __init__(self, path):
        self.path = path
        self.in_lines = self.check_opf(path)


    # This function will check the given opf file to see if it is actually an opf file.
    # Since opf files are zip files, if the file is not a zipfile, this will throw an error!
    # It returns a list of lines read from the db file!
    def check_opf(self, path):
        try:
            with ZipFile(path, 'r') as zpf:
                namelist = zpf.namelist()
                if 'db' in namelist:
                    with zpf.open('db') as dbfile:
                        return dbfile.readlines()
                else:
                    print 'db file is not included in the opf! Exiting'
                    exit()
        except BadZipfile as e:
            print 'The supplied file does not look like an opf file (since it is not a zip file)?'
            print e

    def output(self):
        try:
            with ZipFile(self.path, 'a') as zpf:
                zpf.writestr('db', ''.join(self.in_lines))

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
            print(line)
            if 'pho' in line:
                print('pho code was already added to this file')
                print('skipping the pho code addition')
            else:
                in_lines[i] = add_pho_code(line)




def process():
    for i, line in enumerate(in_lines):
        m = code_reg.search(line)
        if m and 'CHI' in m.groups():
            print line


if __name__ == "__main__":
    myopf = opf_file(sys.argv[1])
    check_pho_code(myopf.in_lines)
    myopf.output()
