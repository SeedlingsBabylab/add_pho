import re
from collections import defaultdict

from cha_re import main_tier_content_pattern, annotation as annotation_pattern, ends_with_a_timestamp,\
    transcription_pattern


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

        # Transcriptions
        self.transcriptions = None
        self.transcription_kinds = None

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

        # These are those multi-line tiers/subtiers
        if line.startswith('\t'):
            # If we are in the sub-tier part then line belongs to a subtier
            if self.sub_tiers_lines_unparsed:
                self.sub_tiers_lines_unparsed.append(line)
            # Otherwise - to the main tier
            else:
                self.main_tier_lines_unparsed.append(line)
            return
        elif line.startswith('%'):
            self.sub_tiers_lines_unparsed.append(line)
            return
        else:
            # The tier must have ended, the next line must start with one of the following lines
            acceptable_prefixes = ('@end', '@bg', '@eg', '*', '\n')
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

    @property
    def _contents_with_multiline_annotations_collapsed(self):
        # Normally, each line ends with a timestamp. If it does not, that means this is a multiline manual
        # annotation. The regex pattern we use to extract annotated words will only work if such an annotation is
        # joined into a single line without the tabs and the line endings (the regex could have been modified to
        # ignore tabs and newlines but we would still need to match against the collapsed line).
        content_line_ = ''
        for content_line in self.contents:
            content_line_ += content_line
            if re.match(ends_with_a_timestamp, content_line):
                yield content_line_
                content_line_ = ''
            else:
                content_line_ = content_line_.rstrip('\n') + ' '

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

        for content_line in self._contents_with_multiline_annotations_collapsed:
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
                speaker_words = [word for word, speaker in zip(words, speakers) if speaker == code]
                if speaker_words:
                    self.words_uttered_by[code] = self.words_uttered_by.get(code, []) + speaker_words

        if code not in self.words_uttered_by:
            self.errors.append(f'Code "{code} found but no annotated words could be identified. Probably a bug.')

    def extract_phonetic_transcriptions(self):
        transcription_subtiers = self.sub_tiers_by_label[TRANSCRIPTION_LABEL]
        if len(transcription_subtiers) == 0:
            return
        if len(transcription_subtiers) > 1:
            self.errors.append('Multiple transcription subtiers')
            return

        contents = self.sub_tiers_by_label[TRANSCRIPTION_LABEL][0].contents
        self.transcriptions = contents.split()
        self.transcription_kinds = [
            'ipa' if re.match(transcription_pattern, transcription) else
            'not transcribed' if transcription == '###' else
            'error'
            for transcription in self.transcriptions]

        for (transcription, kind) in zip(self.transcriptions, self.transcription_kinds):
            if kind == 'error':
                self.errors.append(f'Unexpected transcription: {transcription}')

    def categorize_subtiers(self):
        if len(self.sub_tiers_by_label) > 0:
            raise ValueError('Subtiers are already categorized')

        for sub_tier in self.sub_tiers:
            self.sub_tiers_by_label[sub_tier.label].append(sub_tier)

    def is_speaker_in_annotation(self, speaker_code):
        return any(f'_{speaker_code}_' in content_line for content_line in self.contents)

    def update_pho(self, speaker_code):
        """
        Checks the pho subtier against the annotated words uttered by speaker_code
        :param speaker_code: CHI, MOT, etc.
        :return: str - result of the operation - what's been updated/added or an error message
        """
        if not self.is_speaker_in_annotation(speaker_code):
            return f'{speaker_code} not in annotation'

        # TODO: What if the words have not been extracted yet?
        words = self.words_uttered_by[speaker_code]
        n_words = len(words)
        if n_words == 0:
            return 'error: no words were extracted'

        # TODO: What if the subtiers have not been categorized yet?
        pho_subtiers = self.sub_tiers_by_label[TRANSCRIPTION_LABEL]
        if len(pho_subtiers) == 0:
            pho_subtier = SubTier(label=TRANSCRIPTION_LABEL, contents=(' '.join(['###'] * n_words) + '\n'))
            self.sub_tiers = [pho_subtier] + self.sub_tiers
            self.sub_tiers_by_label[TRANSCRIPTION_LABEL].append(pho_subtier)
            return 'pho subtier added'

        [pho_subtier] = pho_subtiers
        m_transcriptions = len(self.transcriptions)
        # Above, we counted '###' as well as actual transcriptions
        m_transcribed = m_transcriptions - self.transcriptions.count('###')

        if m_transcribed == 0:
            pho_subtier.contents = ' '.join(['###'] * n_words) + '\n'
            self.extract_phonetic_transcriptions()
            if m_transcriptions < n_words:
                return "###'s added, needs transcription"
            elif m_transcriptions > n_words:
                return "###'s removed, needs transcription"
            elif m_transcriptions == n_words:
                return "needs transcription"

        if m_transcriptions > n_words:
            return 'error: more transcriptions than there are words'

        if m_transcriptions < n_words:
            # If we got here, there is at least one actual transcription
            return 'error: fewer transcriptions than there are words, order unknown, sort manually'

        # If we got here, m_transcriptions == n_words

        if m_transcribed < n_words:
            return 'needs some transcription'

        if m_transcribed == n_words:
            return 'all transcribed'

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

    @property
    def main_tiers(self):
        return [object for object in self.partially_parsed if type(object) is MainTier]

    def partially_parse(self):
        """
        Identifies main tiers, leaves all the other lines be.
        self.partially_parsed contains a mix of not-part-of-tier lines as-is and MainTier objects
        self.main_tiers is a list of these objects only
        """
        # do this only once
        if self.partially_parsed:
            raise ValueError('Already partially parsed')

        partially_parsed = list()

        with open(self.path, 'r', encoding='utf-8') as f:
            text = f.readlines()

        main_tier = MainTier()
        for i, line in enumerate(text):
            main_tier.consume(line)

            # The line before this one was the last one of the tier.
            if main_tier.finished:
                partially_parsed.append(main_tier)
                main_tier = MainTier()
                # The current line could have started a new tier
                main_tier.consume(line)

            # We are not inside a tier - keep line as is
            if not main_tier.ongoing:
                partially_parsed.append(line)

        self.partially_parsed = partially_parsed

    def process_for_phonetic_transcription(self, speaker_code):
        """
        Parses main tiers, extracts annotated words, categorizes subtiers, extracts transcriptions.
        Skips the main tiers not mentioning the speaker code
        :param speaker_code: CHI, MOT, etc.
        :return: None
        """
        if not self.partially_parsed:
            self.partially_parse()

        for mt in self.main_tiers:
            # parse
            if not mt.parsed:
                mt.parse()

            # skip if the speaker code is not in the annotations
            if not mt.is_speaker_in_annotation(speaker_code=speaker_code):
                continue

            # extract annotated words
            if speaker_code not in mt.words_uttered_by:
                mt.extract_words_by_speaker(speaker_code)

            # categorize subtiers based on their labels
            if not mt.sub_tiers_by_label:
                mt.categorize_subtiers()

            # Extract transcriptions
            if not mt.transcriptions:
                mt.extract_phonetic_transcriptions()

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

    def write(self, path=None, overwrite_original=False):
        if not path and not overwrite_original:
            raise ValueError('You haven\'t specified the path to write the file to. If you want to overwrite the '
                             'original file, set overwrite_original to True')

        if path and overwrite_original:
            raise ValueError('You\'ve specified the path and set overwrite_original to True - you can only do one of '
                             'those')

        path = path or self.path

        with open(path, 'w') as f:
            f.write(self.compiled)


class SubTier(object):
    def __init__(self, label, contents):
        self.label = label
        self.contents = contents

    @classmethod
    def from_line(cls, line):
        label, contents = line.split('\t', maxsplit=1)
        return cls(label=label, contents=contents)

    def __str__(self):
        return f'{self.label}\t{self.contents}'

    def __repr__(self):
        return str(self)
