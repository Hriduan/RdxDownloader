"""Real local-Git reproductions of the Termux ZIP-import failure. No GitHub requests."""
from contextlib import redirect_stdout, redirect_stderr
import io
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from scripts import release


def git(root,*args,check=True):
    return subprocess.run(['git',*args],cwd=root,check=check,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)


class ImportReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.remote=self.root/'remote.git';git(self.root,'init','--bare',str(self.remote))
        seed=self.root/'seed';seed.mkdir();git(seed,'init','-b','main');self.identity(seed)
        (seed/'README.md').write_text('Original GitHub README\n');(seed/'remote-only.txt').write_text('Preserve this file\n')
        git(seed,'add','.');git(seed,'commit','-m','Original remote history');git(seed,'remote','add','origin',str(self.remote));git(seed,'push','origin','main')
        self.remote_before=git(self.remote,'rev-parse','refs/heads/main').stdout.strip()
        self.local=self.root/'import';self.local.mkdir()
        git(self.local,'init','-b','main');self.identity(self.local);git(self.local,'remote','add','origin',str(self.remote))
        (self.local/'index.html').write_text('RdxDownloader source\n');(self.local/'VERSION').write_text('1.0.0\n')
        (self.local/'README.md').write_text('Updated local README\n');(self.local/'.gitignore').write_text('.env\n')
        (self.local/'.env').write_text('SECRET_FIXTURE=never-upload\n')
    def tearDown(self):self.tmp.cleanup()
    def identity(self,path):
        git(path,'config','user.name','Rdx test fixture');git(path,'config','user.email','fixture@example.invalid')
    def run_helper(self,yes=True):
        args=['release.py']+(['--yes'] if yes else [])
        with patch.object(release,'ROOT',self.local),patch.object(release,'REPO',str(self.remote)),patch('sys.argv',args),redirect_stdout(io.StringIO()):
            release.main()
    def local_commit(self):
        git(self.local,'add','.');git(self.local,'commit','-m','Unrelated local ZIP import')
        return git(self.local,'rev-parse','HEAD').stdout.strip()
    def assert_remote_has(self,path,text):
        self.assertEqual(git(self.remote,'show','main:'+path).stdout,text)
    def test_unrelated_history_reproduced_and_published_without_reset(self):
        head=self.local_commit();(self.local/'index.html').write_text('New user edit\n')
        before=git(self.local,'status','--porcelain').stdout
        self.run_helper()
        self.assertEqual(git(self.local,'rev-parse','HEAD').stdout.strip(),head)
        self.assertEqual(git(self.local,'status','--porcelain').stdout,before)
        self.assertEqual(git(self.remote,'merge-base','--is-ancestor',self.remote_before,'main').returncode,0)
        self.assert_remote_has('index.html','New user edit\n');self.assert_remote_has('README.md','Updated local README\n')
        self.assert_remote_has('remote-only.txt','Preserve this file\n')
        self.assertNotIn('.env',git(self.remote,'ls-tree','-r','--name-only','main').stdout.splitlines())
        self.assertEqual(git(self.remote,'tag','--list').stdout.strip(),'v1.0.0')
    def test_no_local_commits_with_existing_remote(self):
        self.run_helper();self.assertFalse(release.exists('HEAD',cwd=self.local))
        self.assert_remote_has('index.html','RdxDownloader source\n');self.assert_remote_has('remote-only.txt','Preserve this file\n')
    def test_repeat_import_increments_version_and_keeps_remote_lineage(self):
        self.local_commit();self.run_helper();first=git(self.remote,'rev-parse','main').stdout.strip()
        (self.local/'index.html').write_text('Second release edit\n');self.run_helper()
        self.assertEqual((self.local/'VERSION').read_text(),'1.0.1\n')
        self.assertEqual(git(self.remote,'merge-base','--is-ancestor',first,'main').returncode,0)
        self.assertEqual(set(git(self.remote,'tag','--list').stdout.split()),{'v1.0.0','v1.0.1'})
    def test_cancellation_does_not_commit_or_push(self):
        head=self.local_commit()
        with patch('builtins.input',return_value='NO'):self.run_helper(yes=False)
        self.assertEqual(git(self.remote,'rev-parse','main').stdout.strip(),self.remote_before)
        self.assertEqual(git(self.local,'rev-parse','HEAD').stdout.strip(),head)
    def test_normal_clone_descendant_still_uses_normal_release(self):
        clone=self.root/'clone';git(self.root,'clone','--branch','main',str(self.remote),str(clone));self.identity(clone)
        for name in ['index.html','VERSION','.gitignore']:(clone/name).write_bytes((self.local/name).read_bytes())
        self.local=clone;self.run_helper()
        self.assertEqual(git(clone,'rev-parse','HEAD').stdout.strip(),git(self.remote,'rev-parse','main').stdout.strip())
        self.assert_remote_has('remote-only.txt','Preserve this file\n')
    def test_failed_snapshot_push_preserves_local_work_and_remote(self):
        head=self.local_commit();(self.local/'index.html').write_text('Uncommitted work\n')
        hook=self.remote/'hooks/pre-receive';hook.write_text('#!/bin/sh\nexit 1\n');hook.chmod(0o755)
        before=git(self.local,'status','--porcelain').stdout
        with self.assertRaises(subprocess.CalledProcessError):self.run_helper()
        self.assertEqual(git(self.local,'rev-parse','HEAD').stdout.strip(),head)
        self.assertEqual(git(self.local,'status','--porcelain').stdout,before)
        self.assertEqual(git(self.remote,'rev-parse','main').stdout.strip(),self.remote_before)
        self.assertEqual(git(self.remote,'tag','--list').stdout,'')
    def test_dry_run_does_not_initialize_a_repository(self):
        empty=self.root/'no-git';empty.mkdir();(empty/'VERSION').write_text('1.0.0\n')
        with patch.object(release,'ROOT',empty),patch('sys.argv',['release.py','--dry-run']),redirect_stdout(io.StringIO()):release.main()
        self.assertFalse((empty/'.git').exists())
    def test_private_paths_and_escape_rejected(self):
        for rel in ['.env','docs/.env.production','../outside','/absolute','data/file.mp4','node_modules/file.js','private.key']:
            self.assertTrue(release.forbidden(rel),rel)
        self.assertFalse(release.forbidden('.env.example'))


if __name__=='__main__':unittest.main()
