import os
import unittest
from unittest.mock import patch
from server.platforms import normalize_url,platform_for
from server.errors import describe_error
from server.runtime import runtime_options
from scripts.release import next_version
from server.worker import format_catalog

class PlatformUpgradeTests(unittest.TestCase):
    def test_known_platforms_and_subdomains(self):
        for u,f in [('https://youtu.be/abc','youtube'),('https://m.youtube.com/shorts/abc','youtube'),('https://www.facebook.com/reel/123','facebook'),('https://fb.watch/abc/','facebook'),('https://www.instagram.com/reel/ABC/','instagram'),('https://b23.tv/ABC','bilibili'),('https://www.bilibili.com/video/BV1/','bilibili'),('https://vm.tiktok.com/ABC/','tiktok')]:
            self.assertEqual(platform_for(u)['id'],f)
    def test_host_suffix_not_spoofable(self):
        self.assertEqual(platform_for('https://notyoutube.com/x')['id'],'other')
        self.assertEqual(platform_for('https://youtube.com.attacker.example/x')['id'],'other')
    def test_tracking_only_removed_from_known_share_links(self):
        self.assertEqual(normalize_url('https://www.youtube.com/watch?v=abc&si=track&utm_source=x'),'https://www.youtube.com/watch?v=abc')
        u='https://cdn.example/video.mp4?si=signature&utm_source=signed';self.assertEqual(normalize_url(u),u)
    def test_share_url_privacy_guard_remains(self):
        with self.assertRaises(ValueError):normalize_url('http://127.0.0.1/video.mp4')
    def test_classified_errors_do_not_echo_signed_urls(self):
        e=describe_error(Exception('HTTP Error 403 Forbidden https://cdn.example/?token=SECRET'))
        self.assertEqual(e['code'],'source_blocked');self.assertNotIn('SECRET',e['error'])
        self.assertEqual(describe_error(Exception('Sign in to view private video'))['code'],'source_login_required')
        self.assertEqual(describe_error(Exception('No supported JavaScript runtime'))['code'],'runtime_setup')
    def test_deno_only_local_runtime(self):
        with patch.dict(os.environ,{},clear=True),patch('server.runtime.shutil.which',return_value='/opt/deno'):
            self.assertEqual(runtime_options(),{'deno':{'path':'/opt/deno'}})
    def test_missing_deno_no_insecure_node_fallback(self):
        with patch.dict(os.environ,{},clear=True),patch('server.runtime.shutil.which',return_value=None),patch('server.runtime.sys.executable','/missing/python'):self.assertEqual(runtime_options(),{})
    def test_versions_advance_beyond_highest_remote_tag(self):
        self.assertEqual(next_version('1.0.1',['v1.0.9','v1.0.3']),'1.0.10')
        self.assertEqual(next_version('1.0.1',['v2.0.0','not-a-version']),'2.0.1')
        self.assertEqual(next_version('3.0.0',['v2.0.0']),'3.0.0')
    def test_mp4_merge_for_compatible_tracks(self):
        catalog=format_catalog({'formats':[{'format_id':'v','protocol':'https','ext':'mp4','height':1080,'vcodec':'avc1','acodec':'none'}, {'format_id':'a','protocol':'https','ext':'m4a','vcodec':'none','acodec':'mp4a','abr':128}]})
        self.assertEqual(catalog[0]['container'],'mp4')
    def test_direct_media_unknown_codecs_is_not_dropped(self):
        result=format_catalog({'formats':[{'format_id':'mp4','protocol':'https','ext':'mp4','vcodec':None,'acodec':None}]})
        self.assertEqual(len(result),1);self.assertEqual(result[0]['label'],'Source media')
        self.assertEqual(result[0]['audioLabel'],'Audio availability unknown');self.assertIsNone(result[0]['audioId'])
    def test_direct_audio_does_not_invent_bitrate(self):
        result=format_catalog({'formats':[{'format_id':'m4a','protocol':'https','ext':'m4a','vcodec':None,'acodec':None}]})
        self.assertEqual(result[0]['label'],'Source audio');self.assertEqual(result[0]['kind'],'audio')
    def test_av1_opus_retains_compatible_mkv(self):
        catalog=format_catalog({'formats':[{'format_id':'v','protocol':'https','ext':'mp4','height':1080,'vcodec':'av01','acodec':'none'}, {'format_id':'a','protocol':'https','ext':'webm','vcodec':'none','acodec':'opus','abr':128}]})
        self.assertEqual(catalog[0]['container'],'mkv')

if __name__=='__main__':unittest.main()
