import importlib.util
import shutil
import subprocess
import unittest

class ExtractorRoutingTests(unittest.TestCase):
    @unittest.skipUnless(importlib.util.find_spec('yt_dlp'),'yt-dlp required')
    def test_named_urls_have_specific_extractors_without_network(self):
        from yt_dlp.extractor import gen_extractor_classes
        classes=list(gen_extractor_classes())
        for url,prefix in [
            ('https://www.youtube.com/watch?v=BaW_jenozKc','youtube'),
            ('https://www.youtube.com/shorts/BaW_jenozKc','youtube'),
            ('https://www.facebook.com/watch/?v=123456789012345','facebook'),
            ('https://www.instagram.com/reel/C0abc123XYZ/','instagram'),
            ('https://www.bilibili.com/video/BV1xx411c7mD','bilibili'),
            ('https://www.tiktok.com/@fixture/video/7123456789012345678','tiktok')]:
            matching=[c.IE_NAME.lower() for c in classes if c.IE_NAME.lower().startswith(prefix) and c.suitable(url)]
            self.assertTrue(matching,(url,prefix))

class RuntimeSandboxTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('deno'),'Deno needed for runtime sandbox verification')
    def test_local_deno_solver_flags_execute_without_network_permissions(self):
        # Same no-permission/no-remote model used by the installed builtin EJS provider.
        code="console.log(6*7);try{await Deno.readTextFile('/etc/passwd');throw Error('unsafe file access')}catch(e){if(e.name!=='NotCapable'&&e.name!=='PermissionDenied')throw e;console.log('file denied')}try{await fetch('http://127.0.0.1/');throw Error('unsafe network access')}catch(e){if(e.name!=='NotCapable'&&e.name!=='PermissionDenied')throw e;console.log('network denied')}"
        r=subprocess.run([shutil.which('deno'),'run','--no-prompt','--no-remote','--no-config','--no-npm','--cached-only','-'],input=code,capture_output=True,text=True,timeout=15)
        self.assertEqual(r.returncode,0,r.stderr);self.assertIn('42',r.stdout);self.assertIn('file denied',r.stdout);self.assertIn('network denied',r.stdout)

if __name__=='__main__':unittest.main()
