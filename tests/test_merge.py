"""Authorized synthetic-media integration: no third-party videos/ad requests.
Only this test bypasses public-IP checks for its own loopback fixture server.
"""
from contextlib import redirect_stdout
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch

READY=shutil.which('ffmpeg') and shutil.which('ffprobe') and importlib.util.find_spec('yt_dlp')


@unittest.skipUnless(READY,'FFmpeg, ffprobe and yt-dlp needed for synthetic merge integration')
class SyntheticMergeTest(unittest.TestCase):
    def test_exact_resolution_and_audio_are_preserved(self):
        import yt_dlp
        from server import worker
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);src=root/'source';src.mkdir();out=root/'output';out.mkdir()
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=0x3156df:s=640x360:r=24:d=1',
                            '-an','-c:v','libx264','-pix_fmt','yuv420p',str(src/'video.mp4')],check=True)
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','sine=frequency=440:duration=1',
                            '-c:a','aac',str(src/'audio.m4a')],check=True)
            class Quiet(SimpleHTTPRequestHandler):
                def log_message(self,*_):pass
            server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(src)))
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            base=f'http://127.0.0.1:{server.server_port}'
            source={'id':'fixture','title':'Original synthetic test clip','extractor':'fixture','extractor_key':'Fixture',
                    'duration':1,'webpage_url':'https://fixture.example/owned-video','formats':[
                        {'format_id':'v360','url':base+'/video.mp4','protocol':'http','ext':'mp4','height':360,'width':640,'fps':24,'vcodec':'avc1','acodec':'none'},
                        {'format_id':'a128','url':base+'/audio.m4a','protocol':'http','ext':'m4a','vcodec':'none','acodec':'mp4a','abr':128} ]}
            payload={'operation':'download','url':'https://fixture.example/owned-video','selected':{'rawId':'v360','audioId':'a128','container':'mp4'},
                     'directory':str(out),'maxBytes':10*1048576,'maxDuration':60,'rateBytes':4194304}
            def extraction(ydl,*_,**__):
                # Real yt-dlp format selection and native downloading, mocked extraction only.
                return ydl.process_ie_result(source.copy(),download=False)
            output=io.StringIO()
            try:
                with patch('server.worker.install_socket_guard'),patch('server.worker.validate_url',side_effect=lambda u:u),\
                     patch('sys.stdin',io.StringIO(json.dumps(payload))),patch.object(yt_dlp.YoutubeDL,'extract_info',extraction),redirect_stdout(output):
                    worker.main()
                events=[json.loads(line) for line in output.getvalue().splitlines() if line.startswith('{')]
                self.assertTrue(events[-1]['ok']);file=out/events[-1]['file']
                meta=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(file)]))
                video=next(s for s in meta['streams'] if s['codec_type']=='video')
                self.assertEqual((video['width'],video['height']),(640,360))
                self.assertTrue(any(s['codec_type']=='audio' for s in meta['streams']))
                self.assertEqual(file.suffix,'.mp4')
            finally:
                server.shutdown();server.server_close()


if __name__=='__main__':unittest.main()

@unittest.skipUnless(READY,'FFmpeg and yt-dlp needed for synthetic direct media integration')
class SyntheticDirectMediaTest(unittest.TestCase):
    def test_actual_generic_extractor_exposes_direct_mp4(self):
        import yt_dlp
        from server.worker import format_catalog
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=blue:s=320x180:d=1','-c:v','libx264',str(root/'owned.mp4')],check=True)
            class Quiet(SimpleHTTPRequestHandler):
                def log_message(self,*_):pass
            server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=temp));threading.Thread(target=server.serve_forever,daemon=True).start()
            try:
                # Test harness only: trusted loopback fixture; no socket guards are changed.
                with yt_dlp.YoutubeDL({'quiet':True,'no_warnings':True,'allowed_extractors':['default']}) as d:
                    info=d.extract_info(f'http://127.0.0.1:{server.server_port}/owned.mp4',download=False)
                formats=format_catalog(info)
                self.assertTrue(formats);self.assertEqual(formats[0]['container'],'mp4')
                self.assertIsNone(formats[0]['audioId'])
            finally:server.shutdown();server.server_close()
