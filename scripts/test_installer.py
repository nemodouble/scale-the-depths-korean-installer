import hashlib,json,pathlib,tempfile,unittest
import bsdiff4
from unittest.mock import patch
from installer import operate

class InstallerTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name);self.game=self.root/'game';self.pkg=self.root/'pkg';self.game.mkdir();self.pkg.mkdir()
        self.old=b'original unity asset';self.new=b'localized unity asset with Korean UTF8 '+ '한글'.encode()
        delta=bsdiff4.diff(self.old,self.new);(self.pkg/'patch.bin').write_bytes(delta);(self.game/'asset.bundle').write_bytes(self.old)
        sha=lambda x:hashlib.sha256(x).hexdigest()
        self.manifest=dict(preview=False,files=[dict(path='asset.bundle',before=sha(self.old),after=sha(self.new),delta='patch.bin',delta_sha256=sha(delta))])
        self.save()
    def save(self):(self.pkg/'manifest.json').write_text(json.dumps(self.manifest),encoding='utf-8')
    def tearDown(self):self.tmp.cleanup()
    def test_roundtrip_idempotent(self):
        operate(self.game,self.pkg);self.assertEqual((self.game/'asset.bundle').read_bytes(),self.new)
        operate(self.game,self.pkg);operate(self.game,self.pkg,True)
        self.assertEqual((self.game/'asset.bundle').read_bytes(),self.old)
        operate(self.game,self.pkg,True)
    def test_wrong_version_no_write(self):
        (self.game/'asset.bundle').write_bytes(b'updated game')
        with self.assertRaises(RuntimeError):operate(self.game,self.pkg)
        self.assertEqual((self.game/'asset.bundle').read_bytes(),b'updated game')
    def test_corrupt_delta_no_write(self):
        (self.pkg/'patch.bin').write_bytes(b'corrupt')
        with self.assertRaises(RuntimeError):operate(self.game,self.pkg)
        self.assertEqual((self.game/'asset.bundle').read_bytes(),self.old)
    def test_corrupt_backup_no_write(self):
        operate(self.game,self.pkg);(self.game/'KoreanPatch_Backup/asset.bundle').write_bytes(b'corrupt')
        with self.assertRaises(RuntimeError):operate(self.game,self.pkg,True)
        self.assertEqual((self.game/'asset.bundle').read_bytes(),self.new)
    def test_preview_rejected(self):
        self.manifest['preview']=True;self.save()
        with self.assertRaises(RuntimeError):operate(self.game,self.pkg)
    def test_path_traversal_rejected(self):
        self.manifest['files'][0]['path']='../outside';self.save()
        with self.assertRaises(ValueError):operate(self.game,self.pkg)

    def test_running_game_no_write(self):
        with patch('installer.ensure_game_closed',side_effect=RuntimeError('running')):
            with self.assertRaises(RuntimeError):operate(self.game,self.pkg)
        self.assertEqual((self.game/'asset.bundle').read_bytes(),self.old)

    def test_missing_backup_rejected(self):
        (self.game/'asset.bundle').write_bytes(self.new)
        with self.assertRaises(RuntimeError):operate(self.game,self.pkg)
        with self.assertRaises(RuntimeError):operate(self.game,self.pkg,True)

    def test_commit_failure_rolls_back(self):
        import os
        (self.game/'second.bundle').write_bytes(self.old)
        self.manifest['files'].append(dict(self.manifest['files'][0],path='second.bundle'));self.save()
        real=os.replace;calls=0
        def replace(src,dst):
            nonlocal calls
            calls+=1
            if calls==2:raise OSError('simulated locked second file')
            return real(src,dst)
        with patch('installer.os.replace',side_effect=replace):
            with self.assertRaises(OSError):operate(self.game,self.pkg)
        for name in ['asset.bundle','second.bundle']:
            self.assertEqual((self.game/name).read_bytes(),self.old)
        self.assertFalse(list(self.game.glob('.korean-patch-*')))

if __name__=='__main__':unittest.main()
