from pathlib import Path
import os, subprocess, tempfile, unittest
ROOT=Path(__file__).resolve().parents[1]
class ConnectedHostingTests(unittest.TestCase):
    def test_update_defaults_to_yes_without_release_word(self):
        self.assertEqual(self.run_wrapper(), '--yes\n')
    def test_update_review_retains_confirmation(self):
        self.assertEqual(self.run_wrapper('--review'), '\n')
    def test_update_dry_run_remains_non_mutating(self):
        self.assertEqual(self.run_wrapper('--dry-run'), '--yes --dry-run\n')
    def run_wrapper(self,*args):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            for name,body in [('python3','#!/bin/sh\nshift\nprintf "%s\\n" "$*"\n'),('gh','#!/bin/sh\nexit 1\n')]:
                file=p/name;file.write_text(body);file.chmod(0o755)
            result=subprocess.run(['/bin/bash',str(ROOT/'update'),*args],env={**os.environ,'PATH':str(p)+':/usr/bin:/bin'},capture_output=True,text=True,check=True)
            return result.stdout
    def test_pages_default_is_real_https_backend(self):
        s=(ROOT/'assets/js/config.js').read_text();self.assertIn('https://rdxdownloader.onrender.com',s);self.assertIn("location.hostname === 'hriduan.github.io'",s)
    def test_generated_fixture_has_audio_and_video(self):
        import json
        r=subprocess.run(['ffprobe','-v','error','-show_streams','-of','json',str(ROOT/'tests/fixtures/authorized-sample.mp4')],capture_output=True,text=True,check=True)
        kinds={s['codec_type'] for s in json.loads(r.stdout)['streams']};self.assertIn('audio',kinds);self.assertIn('video',kinds)

class DirectTopLevelFormatTests(unittest.TestCase):
    def test_top_level_direct_mp4_catalog_is_not_empty(self):
        from server.worker import format_catalog
        info={'url':'https://example.com/clip.mp4','format_id':'0','ext':'mp4','protocol':'https','vcodec':None,'acodec':None}
        rows=format_catalog(info);self.assertEqual(len(rows),1);self.assertEqual(rows[0]['rawId'],'0');self.assertEqual(rows[0]['kind'],'video')
    def test_top_level_drm_does_not_become_eligible(self):
        from server.worker import source_formats
        self.assertEqual(source_formats({'url':'https://example.com/clip.mp4','ext':'mp4','protocol':'https','has_drm':True}),[])
    def test_top_level_unsafe_protocol_is_not_added(self):
        from server.worker import source_formats
        self.assertEqual(source_formats({'url':'file:///tmp/video.mp4','ext':'mp4','protocol':'file'}),[])
