"""Resource-limited parser subprocess entry point."""
import json,os,sys
from pathlib import Path

def main():
 try:
  import resource
  resource.setrlimit(resource.RLIMIT_CPU,(300,300));resource.setrlimit(resource.RLIMIT_AS,(3*1024**3,3*1024**3))
 except ImportError:pass
 from .parsing import ParserRouter,XMLParser
 path,pid,out=sys.argv[1:]
 if Path(path).suffix.lower()=='.xml':document=XMLParser().parse(path,pid);external={'dual_parser':{'status':'NOT EXECUTED','reason':'XML_SOURCE'}}
 else:document,external=ParserRouter(grobid_url=os.getenv('GROBID_URL'),docling_command=os.getenv('DOCLING_COMMAND')).parse(path,pid)
 Path(out).write_text(json.dumps({'document':document.model_dump(mode='json'),'external':external},ensure_ascii=False))
if __name__=='__main__':main()
