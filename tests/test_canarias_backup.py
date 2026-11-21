import json
import sqlite3
import tempfile
import unittest
import zipfile
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
import canarias_backup as backup


class BackupTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.data=self.root/'data'
        self.storage=self.data/'almacen'
        self.storage.mkdir(parents=True)
        (self.storage/'doc.pdf').write_bytes(b'original')
        self.db=self.data/'datos'/'evaluafp.sqlite3'
        self.db.parent.mkdir()
        with closing(sqlite3.connect(self.db)) as d:
            d.executescript("""
              CREATE TABLE modules(id INTEGER PRIMARY KEY);
              CREATE TABLE students(id INTEGER PRIMARY KEY);
              CREATE TABLE outcomes(id INTEGER PRIMARY KEY);
              CREATE TABLE criteria(id INTEGER PRIMARY KEY);
              CREATE TABLE preferences(key TEXT PRIMARY KEY,value TEXT);
              CREATE TABLE programmings(id INTEGER PRIMARY KEY,local_path TEXT);
              INSERT INTO modules VALUES(1);
            """)
            d.execute('INSERT INTO programmings VALUES(1,?)',(str(self.storage/'doc.pdf'),))
            d.commit()

    def make(self):
        return backup.make(self.data,self.root/'backups',self.db,self.storage)

    def test_unique_archives_and_restore(self):
        first=self.make()
        second=self.make()
        self.assertNotEqual(first,second)
        self.assertEqual(len(backup.verify(first)['files']),2)
        dest=backup.restore(first,self.root/'recovered')
        self.assertEqual((dest/'almacen'/'doc.pdf').read_bytes(),b'original')
        with closing(sqlite3.connect(dest/backup.DB_MEMBER)) as d:
            self.assertEqual(d.execute('SELECT local_path FROM programmings').fetchone()[0],
                             str(dest/'almacen'/'doc.pdf'))
        with self.assertRaises(ValueError):
            backup.restore(second,dest)
        self.assertTrue(self.db.exists())

    def test_reject_traversal_and_cleanup(self):
        bad=self.root/'bad.zip'
        with zipfile.ZipFile(bad,'w') as z:
            z.writestr('../outside.txt','bad')
        dest=self.root/'failed'
        with self.assertRaises(ValueError):
            backup.restore(bad,dest)
        self.assertFalse(dest.exists())
        self.assertFalse((self.root/'outside.txt').exists())

    def test_modified_member_rejected(self):
        good=self.make()
        bad=self.root/'tampered.zip'
        with zipfile.ZipFile(good) as src,zipfile.ZipFile(bad,'w') as dst:
            for name in src.namelist():
                dst.writestr(name,b'modified' if name=='almacen/doc.pdf' else src.read(name))
        with self.assertRaises(ValueError):
            backup.verify(bad)


    def test_graphical_recovery_only_local_and_confirmed(self):
        good=self.make()
        listing=backup.list_archives(good.parent)
        self.assertEqual([r['name'] for r in listing],[good.name])
        for name,confirmed in [(good.name,False),('../'+good.name,True),('absent.zip',True)]:
            with self.assertRaises(ValueError):
                backup.recover_archive(good.parent,self.data,name,confirmed)
        result=backup.recover_archive(good.parent,self.data,good.name,True)
        self.assertTrue(result['active_data_unchanged'])
        dest=Path(result['path'])
        self.assertEqual(dest.parent.resolve(),self.data.parent.resolve())
        self.assertNotEqual(dest,self.data)
        self.assertTrue((dest/backup.DB_MEMBER).is_file())
        self.assertTrue(self.db.is_file())
