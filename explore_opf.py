from pathlib import Path
from zipfile import ZipFile


class OPFFile(object):
    def __init__(self, path):
        self.path = path
        self.db, self.project = self.load()

    def load(self):
        with ZipFile(self.path, 'r') as zpf:
            assert set(zpf.namelist()) == {'db', 'project'}

            # Annotations
            with zpf.open('db', 'r') as f:
                db = f.read().splitlines()
            # zpf.open read file in binary mode
            db = [line.decode('utf-8') for line in db]

            # Metadata
            with zpf.open('project', 'r') as f:
                project = f.read()

        return db, project


opf_path = Path('01_17_sparse_code.opf')
opf = OPFFile(opf_path)
