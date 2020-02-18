from zipfile import ZipFile, BadZipfile
import re, sys, pdb




code_reg = re.compile(r'\(.*,[a-z],[a-z],([A-Z]{3}),.*\)')

# This function will check the given opf file to see if it is actually an opf file.
# Since opf files are zip files, if the file is not a zipfile, this will throw an error!
# It returns a list of lines read from the db file!
def check_opf(path):
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

def check_pho_column(in_lines):
    for line in in_lines:
        if 'labeled_object' in line:
            print line
    else:
        print 'Header line is not present in the db file!'
        exit()

def process():
    for i, line in enumerate(in_lines):
        m = code_reg.search(line)
        if m and 'CHI' in m.groups():
            print line


if __name__ == "__main__":
    in_lines = check_opf(sys.argv[1])
    check_pho_column(in_lines)
