class MainTier(object):
    def __init__(self):
        self.ongoing = False
        self.finished = False
        self.main_tier_lines_unparsed = list()
        self.sub_tiers = list()
        self.label = None
        self.contents = None

    def consume(self, line):
        """
        Checks whether line belongs to a main tier or not. If it does, saves it.
        :param line: one more string from the cha file
        """
        # If a tier has not started yet, ignore anything but *
        if not self.ongoing:
            if not line.startswith('*'):
                return
            else:
                self.ongoing = True
                self.main_tier_lines_unparsed.append(line)
                return

        # If we got here, we are in the middle of building the tier

        # These are those multi-line tiers
        if line.startswith('\t'):
            # There shouldn't be lines like this, once we are in the sub-tier part.
            if self.sub_tiers:
                raise ValueError('A line starts with a tab after the sub-tiers started')
            self.main_tier_lines_unparsed.append(line)
            return
        elif line.startswith('%'):
            self.sub_tiers.append(line)
            return
        else:
            # The tier must have ended, the next line must start with one of the following lines
            acceptable_prefixes = ('@end', '@bg', '@eg', '*')
            line_ = line.lower()
            if any(line_.startswith(prefix) for prefix in acceptable_prefixes):
                self.finished = True
                return
            else:
                raise ValueError('Unexpected line within a tier:\n{}')

    def parse_main(self):
        """

        :return:
        """
        if self.label:
            raise ValueError('Already parsed the main part')

        # Each line has two parts separated by a tab
        starts, ends = zip(*[line.split('\t', maxsplit=1) for line in self.main_tier_lines_unparsed])
        # Only the first line should have non-empty first part
        assert set(starts[1:]) <= {''}
        # This part is the tier label.
        self.label = starts[0]
        # The second parts of the lines are the content lines
        self.contents = ends

        # Remove unparsed
        self.main_tier_lines_unparsed = None

    def __str__(self):
        if self.main_tier_lines_unparsed:
            main = ''.join(self.main_tier_lines_unparsed)
        else:
            main = '\t'.join([self.label] + list(self.contents))
        sub = ''.join(self.sub_tiers)
        return main + sub

    def __repr__(self):
        return str(self)


class CHAFile(object):
    def __init__(self, path):
        self.path = path
        self.partially_parsed = None
        self.main_tiers = None

    def partially_parse(self):
        """
        Identifies main tiers, leaves all the other lines be.
        self.partially_parsed contains a mix of not-part-of-tier lines as-is and MainTier objects
        self.main_tiers is a list of these objects only
        """
        # do this only once
        if self.partially_parsed:
            raise ValueError('Already partially parsed')

        self.partially_parsed = list()
        self.main_tiers = list()

        with open(self.path, 'r', encoding='utf-8') as f:
            text = f.readlines()

        main_tier = MainTier()
        for i, line in enumerate(text):
            main_tier.consume(line)

            # The line before this one was the last one of the tier.
            if main_tier.finished:
                self.partially_parsed.append(main_tier)
                self.main_tiers.append(main_tier)
                main_tier = MainTier()
                # The current line could have started a new tier
                main_tier.consume(line)

            # We are not inside a tier - keep line as is
            if not main_tier.ongoing:
                self.partially_parsed.append(line)

    @property
    def compiled(self):
        """
        Converts contents back to text.
        :return: one long string
        """
        if self.partially_parsed:
            return ''.join(map(str, self.partially_parsed))
        else:
            raise ValueError('Not parsed, nothing to compile')

    def __str__(self):
        if self.partially_parsed:
            return self.compiled
        else:
            return f'Not parse cha file at {self.path}'

    def no_changes(self):
        """
        Compares current state to the original text
        :return: bool
        """
        return open(self.path, 'r').read() == self.compiled