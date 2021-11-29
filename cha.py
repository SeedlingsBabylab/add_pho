import re
from collections import defaultdict

from cha_re import main_tier_content_pattern, annotation as annotation_pattern


TRANSCRIPTION_LABEL = '%pho:'


class MainTier(object):
    def __init__(self):
        # A main tier is initially built by feeding it one line from the cha file at a time
        self.ongoing = False
        self.finished = False
        # The lines are saved as a list
        self.main_tier_lines_unparsed = list()
        self.sub_tiers_lines_unparsed = list()

        # The tier-level parsing breaks the lines into the label and content parts
        self.parsed = False
        self.label = None
        self.contents = None
        self.sub_tiers = None  # A list of SubTier objects

        # Parse out the annotated words
        self.words_uttered_by = dict()

        # Categorize the subtiers
        self.sub_tiers_by_label = defaultdict(list)

        # If something breaks on the way, write it down and continue ahead
        self.errors = list()

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
            if self.sub_tiers_lines_unparsed:
                raise ValueError('A line starts with a tab after the sub-tiers started')
            self.main_tier_lines_unparsed.append(line)
            return
        elif line.startswith('%'):
            self.sub_tiers_lines_unparsed.append(line)
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

    def _parse_main(self):
        """

        :return:
        """
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

    def _parse_sub_tiers(self):
        self.sub_tiers = [SubTier.from_line(sub_tier_line) for sub_tier_line in self.sub_tiers_lines_unparsed]
        self.sub_tiers_lines_unparsed = None

    def parse(self):
        if self.parsed:
            raise ValueError('Already parsed')
        self._parse_main()
        self._parse_sub_tiers()
        self.parsed = True

    def extract_words_by_speaker(self, code):
        """
        Finds word uttered by a speaker annotated as code
        :param code: CHI, MOT, etc.
        :return: None
        """
        # Do this just once if any words were found the first time
        if code in self.words_uttered_by:
            raise ValueError(f'Words uttered by {code} have already been extracted')

        # Don't do anything if the speaker code is not present at all
        if f'_{code}_' not in str(self):
            return

        for content_line in self.contents:
            # re will only capture the last match of each group so
            # we will extract all the annotations in one step and
            # then find all words and speakers within them
            parsed = re.match(main_tier_content_pattern, content_line)
            if not parsed:
                self.errors.append(f'The following line could not be parsed:\n{content_line}')
                continue

            annotations = parsed.group('annotations')
            if any(annotations):
                words, speakers = zip(*re.findall(annotation_pattern, annotations))
                speaker_words = [word for word, speaker in zip(words, speakers) if speaker == 'CHI']
                if speaker_words:
                    self.words_uttered_by[code] = self.words_uttered_by.get(code, []) + speaker_words

        if code not in self.words_uttered_by:
            self.errors.append(f'Code "{code} found but no annotated words could be identified. Probably a bug.')

    def categorize_subtiers(self):
        if len(self.sub_tiers_by_label) > 0:
            raise ValueError('Subtiers are already categorized')

        for sub_tier in self.sub_tiers:
            self.sub_tiers_by_label[sub_tier.label].append(sub_tier)

    def __str__(self):
        if not self.parsed:
            main = ''.join(self.main_tier_lines_unparsed)
            sub = ''.join(self.sub_tiers_lines_unparsed)
        else:
            main = '\t'.join([self.label] + list(self.contents))
            sub = ''.join(map(str, self.sub_tiers))

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


class SubTier(object):
    def __init__(self, label, contents):
        self.label = label
        self.contents = contents

    @classmethod
    def from_line(cls, line):
        label, contents = line.split('\t')
        return cls(label=label, contents=contents)

    def __str__(self):
        return f'{self.label}\t{self.contents}'

    def __repr__(self):
        return str(self)
