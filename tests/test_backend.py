import contextlib
import io
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request
from server import app
from server.network import public_ip, validate_url
from server.worker import eligible, format_catalog
from scripts.release import next_version


class NetworkTests(unittest.TestCase):
    def test_reject_nonpublic_ips(self):
        for ip in ['127.0.0.1','10.0.0.1','192.168.0.1','169.254.169.254','::1','fc00::1','::ffff:127.0.0.1','224.0.0.1','0.0.0.0','64:ff9b::a00:1','2002:0a00:0001::']:
            self.assertFalse(public_ip(ip), ip)
    def test_public_ips(self):
        for ip in ['8.8.8.8','1.1.1.1','2606:4700:4700::1111']:
            self.assertTrue(public_ip(ip))
    def test_bad_urls(self):
        for u in ['file:///etc/passwd','ftp://example.com/x','https://user:pass@example.com','http://127.0.0.1/a','http://[::1]','https://metadata.internal','https://localhost.','https://example.com:8080/x','not a url','https://example.com/\n']:
            with self.assertRaises(ValueError, msg=u): validate_url(u, resolve=False)
    def test_mixed_dns_answers_rejected(self):
        with patch('server.network.socket.getaddrinfo', return_value=[(2,1,6,'',('8.8.8.8',443)),(2,1,6,'',('127.0.0.1',443))]):
            with self.assertRaises(ValueError): validate_url('https://example.com/a')
    def test_socket_boundary_rejects_private_destination(self):
        # Isolate global socket patch in a subprocess; this makes no network requests.
        script="from server.network import install_socket_guard;import socket;install_socket_guard();s=socket.socket();\ntry:s.connect(('127.0.0.1',80));raise SystemExit(2)\nexcept OSError:pass\n"
        self.assertEqual(subprocess.run([sys.executable,'-c',script],cwd=app.ROOT).returncode,0)


class FormatTests(unittest.TestCase):
    def setUp(self):
        self.formats=[{'format_id':'137','protocol':'https','ext':'mp4','height':1080,'vcodec':'avc1','acodec':'none','filesize':200},
                      {'format_id':'140','protocol':'https','ext':'m4a','vcodec':'none','acodec':'mp4a','abr':128,'filesize':100},
                      {'format_id':'18','protocol':'https','ext':'mp4','height':360,'vcodec':'avc1','acodec':'mp4a','filesize':100},
                      {'format_id':'drm','protocol':'https','ext':'mp4','height':2160,'vcodec':'avc1','has_drm':True},
                      {'format_id':'rtmp','protocol':'rtmp','ext':'flv','vcodec':'h264'}]
    def test_audio_merge_and_source_resolution(self):
        result=format_catalog({'formats':self.formats});self.assertEqual(len(result),3)
        best=result[0];self.assertEqual(best['label'],'1080p');self.assertEqual(best['audioId'],'140');self.assertEqual(best['container'],'mp4');self.assertEqual(best['size'],300)
        self.assertEqual([f['height'] for f in result if f['kind']=='video'],[1080,360])
    def test_existing_audio_not_downloaded_twice(self):
        f=next(f for f in format_catalog({'formats':self.formats}) if f['rawId']=='18')
        self.assertIsNone(f['audioId']);self.assertEqual(f['container'],'mp4')
    def test_no_audio_promise_for_silent_source(self):
        f=format_catalog({'formats':[self.formats[0]]})[0]
        self.assertEqual(f['audioLabel'],'Silent source video')
    def test_selector_characters_not_allowed(self):
        f={**self.formats[0],'format_id':'bestvideo+bestaudio'};self.assertFalse(eligible(f))
    def test_drm_and_external_protocol_not_allowed(self):
        self.assertFalse(eligible(self.formats[-1]));self.assertFalse(eligible(self.formats[-2]))
    def test_release_sequence(self):
        self.assertEqual(next_version('1.0.0',[]),'1.0.0');self.assertEqual(next_version('1.0.0',['v1.0.0']),'1.0.1');self.assertEqual(next_version('1.0.9',['v1.0.9']),'1.0.10')


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=app.Server(('127.0.0.1',0),app.Handler);cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start();cls.base=f'http://127.0.0.1:{cls.server.server_port}'
    @classmethod
    def tearDownClass(cls): cls.server.shutdown();cls.server.server_close()
    def setUp(self): app.rate_log.clear();app.jobs.clear();app.inspections.clear()
    def request(self,path,data=None,origin=None,method=None):
        headers={'Content-Type':'application/json'}
        if origin:headers['Origin']=origin
        request=urllib.request.Request(self.base+path,data=json.dumps(data).encode() if data is not None else None,headers=headers,method=method)
        try:return urllib.request.urlopen(request,timeout=5)
        except urllib.error.HTTPError as e:return e
    def test_health_and_root(self):
        r=self.request('/api/health');self.assertEqual(r.status,200);self.assertEqual(json.load(r)['service'],'RdxDownloader')
        self.assertIn(b'Keep the',self.request('/').read())
    def test_head_has_no_body(self):
        r=self.request('/index.html',method='HEAD');self.assertEqual(r.status,200);self.assertEqual(r.read(),b'')
    def test_static_source_private_paths_rejected(self):
        for p in ['/server/app.py','/.env','/.git/config','/docs/DEPLOYMENT.md','/assets/../server/app.py','/assets/%2e%2e/server/app.py','/assets/']:
            self.assertEqual(self.request(p).status,404,p)
    def test_permission_required(self):
        self.assertEqual(self.request('/api/inspect',{'url':'https://example.com'}).status,400)
    def test_unsupported_origin_rejected(self):
        self.assertEqual(self.request('/api/inspect',{'permission':True,'url':'https://example.com'},origin='https://attacker.example').status,403)
    def test_inspection_endpoint_mock(self):
        with patch('server.app.inspect',return_value={'inspection':'fixture','formats':[]}):
            r=self.request('/api/inspect',{'permission':True,'url':'https://example.com'});self.assertEqual(r.status,200);self.assertEqual(json.load(r)['inspection'],'fixture')
    def test_invalid_format_capability(self):
        with patch('server.app.settings_ready',return_value=True):
            self.assertEqual(self.request('/api/download',{'permission':True,'inspection':'not-real','format':'best'}).status,410)
    def test_rate_limit(self):
        with patch('server.app.inspect',return_value={'formats':[]}):
            for _ in range(8):self.assertEqual(self.request('/api/inspect',{'permission':True,'url':'https://example.com'}).status,200)
            self.assertEqual(self.request('/api/inspect',{'permission':True,'url':'https://example.com'}).status,429)
    def test_bearer_job_does_not_leak_path(self):
        import time
        app.jobs['test-token']={'status':'ready','created':time.time(),'file':'/private/secret','name':'safe.mp4','progress':100}
        r=json.load(self.request('/api/jobs/test-token'));self.assertNotIn('file',r);self.assertEqual(r['downloadUrl'],'/api/files/test-token')
    def test_missing_job(self):self.assertEqual(self.request('/api/jobs/not-real').status,404)


if __name__=='__main__':unittest.main()
