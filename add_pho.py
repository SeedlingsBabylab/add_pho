import argparse, re, sys, pdb

# Code for annotation regex. The speaker code should be group number -3
code_regx = re.compile(r'([a-zA-Z][a-z+]*)( +)(&=)([A-Za-z]{1})(_)([A-Za-z]{1})(_)([A-Z]{1}[A-Z0-9]{2})(_)?(0x[a-z0-9]{6})?', re.IGNORECASE | re.DOTALL) # Annotation regex

def get_args():
    parser = argparse.ArgumentParser(description='Add pho tiers for each child utterance.')
    parser.add_argument('input_file', help='The cha/opf file to which pho lines will be added.')
    parser.add_argument('--output_path', help='Path of the output file, which is the updated cha file, with pho lines added.')
    return parser.parse_args()

# Given the index of CHI line, check if there is an associated pho!
# This check using the first character of the cha file line seems OK, 
# but there might be a bug of some sort that I am missing. 
def check_pho(ind, lines):
    # Start from the next line to CHI line
    for l in lines[ind+1:]:
        if '%pho' in l:
            return True
        if l[0] in ['@', '*', '%']:
            return False
    
    sys.stderr.write('Code should not have arrived this point. Try pdb?\n')
    return False

# This function DOES NOT actually insert pho lines. It simply finds the indices to insert them. 
def insert_pho(ind, lines, pos_list):
    # Call helper function to find the number of utterances (if this is a multiline 
    # annotation or (more commonly) if there is more than one utterance per line, 
    # AND, the exact position to insert the pho lines. 
    num, pos = count_utterances(ind, lines)
    print 'num: {}, pos: {}'.format(num, pos)

    pos_list.append((num, pos))


def create_pho_line(num):
    return '%pho:\t{}\n'.format(' '.join([4 * '#' for i in range(num)]))


# ind is the index of the line where 'CHI' was found.     
def count_utterances(ind, lines):
    end = find_end(ind, lines)
    if end:
        # Combining the multiline into a single line for searching with the annotation regx
        megaline = ' '.join(lines[ind:ind+end])
        m = re.findall(code_regx, megaline)
        print m
        print lines[ind+end]
    return len(m), ind+end
        
# Helper function to find the next annotation/comment/section (finding the limits of multiline annotations)
def find_end(ind, lines):
    # We start from the next line because the line with CHI in it certainly starts with a *CHN or sth along those lines. 
    for i, l in enumerate(lines[ind+1:]):
        if l[0] in ['@', '*', '%']:
            # Returning plus one here because we search for the end starting from +1 of index above!
            return i + 1
    else:
        print 'No end found starting from index {}'.format(ind)
        # Returning zero means that something was wrong?
        return 0

def output_to_file(outlines, output_path):
    with open(output_path, 'w') as outf:
        outf.writelines(outlines)

# This function ACTUALLY inserts the pho lines into outlines, taking into account that each insertion will move the index of next insertion by one.
def real_insert(pos_list, out_lines):
    for i, item in enumerate(pos_list):
        #pdb.set_trace()
        print item
        out_lines.insert(item[1] + i, create_pho_line(item[0]))

# This function is used to add pho lines into cha files.
def add_pho_2_cha(input_file, output_path):
    with open(input_file) as inf:
        in_lines = inf.readlines()

    # Make a copy of the input lines to insert the pho lines into!
    out_lines = in_lines[:]
    pos_list = []
    for i, line in enumerate(in_lines):
        m = code_regx.search(line)
        if m and 'CHI' in m.groups():
            # If there is already a pho line, we don't add anything. 
            if check_pho(i, in_lines):
                continue
            # If there is no pho line, then we need to add stuff!
            else:
                insert_pho(i, in_lines, pos_list)
    if output_path:
        print 'output path option specified!'
        real_insert(pos_list, out_lines)
        output_to_file(out_lines, output_path)
    return

# This function is used to add pho lines into pho files.
def add_pho_2_opf(input_file, output_path):
    return


if __name__ == '__main__':
    args = get_args()
    print 'Input file is {}'.format(args.input_file)
    add_pho_2_cha(args.input_file, args.output_path)


