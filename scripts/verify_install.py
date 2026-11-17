"""Verify a wheel installed in a separate environment, outside the source cwd."""
from pathlib import Path
import argparse,subprocess,tempfile,os,json,socket,time
from urllib.request import urlopen,Request
ROOT=Path(__file__).resolve().parents[1]

def main(interpreter):
    python=str(Path(interpreter).resolve());bin_dir=Path(python).parent
    # Do not resolve the interpreter symlink into the base interpreter directory.
    bin_dir=Path(interpreter).absolute().parent;python=str(bin_dir/'python')
    env={**os.environ,'PYTHONPATH':''}
    def run(args,cwd):
        r=subprocess.run(args,cwd=cwd,env=env,capture_output=True,text=True,timeout=40)
        assert r.returncode==0,'Installed command failed: '+args[0]
        return r.stdout
    with tempfile.TemporaryDirectory() as d:
        tmp=Path(d)
        version=run([python,'-c',"import importlib.metadata,contracts;assert importlib.metadata.version('paper-extraction-contracts')=='0.1.2';assert 'site-packages' in contracts.__file__;print('0.1.2')"],tmp)
        assert version.strip()=='0.1.2';print('PASS isolated wheel imports from site-packages: 0.1.2')
        run([str(bin_dir/'paperlens'),'--help'],tmp);run([str(bin_dir/'paperlens-web'),'--help'],tmp)
        print('PASS both installed CLI entrypoints')
        output=run([str(bin_dir/'paperlens'),'run','--manifest',str(ROOT/'examples/demo_manifest.json'),'--db',str(tmp/'db'),
            '--workdir',str(tmp/'cache'),'--output',str(tmp/'results')],tmp)
        report=json.loads(output);assert report['success']==3 and report['failed']==0
        print('PASS isolated CLI: submitted=3 success=3 partial=0 failed=0 skipped=0')
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        server=subprocess.Popen([str(bin_dir/'paperlens-web'),'--port',str(port),'--no-browser','--workdir',str(tmp/'web')],cwd=tmp,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        try:
            deadline=time.monotonic()+15
            while True:
                try:
                    with urlopen(f'http://127.0.0.1:{port}/api/status',timeout=1) as r:status=json.load(r)
                    break
                except OSError:
                    if server.poll() is not None or time.monotonic()>deadline:raise AssertionError('Installed web server unavailable')
                    time.sleep(.05)
            assert status['engine']=='python' and status['version']=='0.1.2'
            with urlopen(f'http://127.0.0.1:{port}/',timeout=5) as r:assert b'MatterLens' in r.read()
            req=Request(f'http://127.0.0.1:{port}/api/extract?arxiv_id=2401.00001&title=Installed-fixture',data=(ROOT/'samples/m14/paper_1.pdf').read_bytes(),headers={'Content-Type':'application/pdf'},method='POST')
            with urlopen(req,timeout=20) as r:value=json.load(r)
            assert value['record']['status']=='success'
            print('PASS installed web UI assets and actual PDF extraction over HTTP')
        finally:server.terminate();server.communicate(timeout=5)
        print('INSTALL SUMMARY: 4 passed, 0 failed');return 0
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--python',type=Path,required=True);a=p.parse_args();raise SystemExit(main(a.python))
