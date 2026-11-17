"""Independent structured parsers; uncertainty is data, not silently repaired meaning."""
from abc import ABC,abstractmethod
from pathlib import Path
from difflib import SequenceMatcher
import hashlib,json,re,shutil,subprocess,tempfile
from xml.etree import ElementTree as ET
import httpx
import pymupdf as fitz
from parsers.pdf import PDFParser
from parsers.cleaning import LayoutCleaner
from parsers.reading_order import ordered_blocks,role_key
from .models import ParsedDocument,Segment,Equation
from .errors import PlatformError

HEADINGS={
 'abstract':'abstract','introduction':'introduction','background':'introduction','related work':'related_work',
 'related works':'related_work','preliminaries':'preliminaries','problem formulation':'problem','problem statement':'problem',
 'methods':'methodology','method':'methodology','methodology':'methodology','materials and methods':'methodology',
 'experimental':'methodology','experimental section':'methodology','experimental procedures':'methodology',
 'computational details':'methodology','calculation details':'methodology','algorithm':'algorithm','algorithms':'algorithm',
 'proposed method':'methodology','approach':'methodology','experiments':'experiments','experimental evaluation':'experiments',
 'evaluation':'experiments','results':'results','results and discussion':'results','results and discussions':'results',
 'discussion':'discussion','limitations':'limitations','conclusions':'conclusions','conclusion':'conclusions',
 'conclusion and future work':'conclusions','future work':'future_work','references':'references','bibliography':'references',
 'acknowledgments':'acknowledgements','acknowledgements':'acknowledgements','funding':'acknowledgements',
 'appendix':'appendix','supplementary information':'appendix','supplemental material':'appendix',
}
EXCLUDED={'references','acknowledgements','caption','margin','figure'}
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def heading(text):
 s=re.sub(r'^(?:\d+(?:\.\d+)*[.)]?|[IVXLCDM]+[.)])\s+','',text.strip(),flags=re.I).rstrip(':.').casefold()
 return HEADINGS.get(s) if len(s)<90 else None
class BaseScientificParser(ABC):
 @abstractmethod
 def parse(self,path,paper_id)->ParsedDocument:...

class PyMuPDFParser(BaseScientificParser):
 version='science-layout-1+pymupdf-'+fitz.VersionBind
 def parse(self,path,paper_id):
  raw=PDFParser().parse(Path(path));reader=PDFParser();layout=reader.layout_hints(path);cleaned=LayoutCleaner().apply(raw,layout=layout)
  ordered,roles=ordered_blocks(cleaned,layout);segments=[];equations=[];section=None;kind='front_matter'
  for b in ordered:
   role=roles.get(role_key(b));a=b.raw_start
   if role:
    segments.append(Segment(segment_id=f'{b.block_id}:{a}',text=b.text,page=b.page_number,section=section,kind=role,bbox=b.bbox,source_path=f'{b.block_id}[{a}:{b.raw_end}]'));continue
   chunk=[];start=a
   def flush():
    if chunk:
     text=''.join(chunk)
     if text.strip():segments.append(Segment(segment_id=f'{b.block_id}:{start}',text=text,page=b.page_number,section=section,kind=kind,bbox=b.bbox,source_path=f'{b.block_id}[{start}:{start+len(text)}]'))
   for line in b.text.splitlines(keepends=True):
    found=heading(line);hint=layout.get((b.block_id,a),{})
    strong=hint.get('bold') or hint.get('size',0)>hint.get('body_size',10)*1.07
    if found and (strong or line.strip().casefold() in {'references','bibliography','acknowledgements','acknowledgments'}):
     flush();chunk=[];section=line.strip();kind=found
     segments.append(Segment(segment_id=f'{b.block_id}:{a}:heading',text=line,page=b.page_number,section=section,kind='heading',bbox=b.bbox,source_path=f'{b.block_id}[{a}:{a+len(line)}]'));start=a+len(line)
    else:
     if not chunk:start=a
     chunk.append(line)
    a+=len(line)
   flush()
  for segment in segments:
   if segment.kind in EXCLUDED or segment.kind=='heading':continue
   for line in segment.text.splitlines():
    if 4<=len(line.strip())<=240 and re.search(r'[=≡≈∝]',line):
     equations.append(Equation(text=line,context_segment_ids=(segment.segment_id,),parse_status='PARSE_UNCERTAIN'))
  warnings=['MATHEMATICAL_TEXT_REQUIRES_REVIEW'] if equations else []
  warnings+=['UNKNOWN_SECTION:'+s.segment_id for s in segments if s.section is None and s.kind not in EXCLUDED]
  # Preserve figures and actual table cells separately; never mix captions into methods.
  with fitz.open(path) as doc:
   for page_no,page in enumerate(doc,1):
    for i,image in enumerate(page.get_image_info()):
     box=tuple(float(x) for x in image['bbox']);segments.append(Segment(segment_id=f'p{page_no}:figure:{i}',text='',page=page_no,section=None,kind='figure',bbox=box,source_path=f'page/{page_no}/image/{i}'))
    if len(page.get_drawings())>=8:
     try:
      tables=page.find_tables().tables
      for i,table in enumerate(tables):
       rows=table.extract();text='\n'.join('\t'.join(v or '' for v in row) for row in rows)
       segments.append(Segment(segment_id=f'p{page_no}:table:{i}',text=text,page=page_no,section='Table',kind='table',bbox=tuple(float(x) for x in table.bbox),source_path=f'page/{page_no}/table/{i}'))
       warnings.append('TABLE_LAYOUT_CANDIDATE:p'+str(page_no))
     except (AttributeError,ValueError,RuntimeError):warnings.append('TABLE_PARSER_UNAVAILABLE:p'+str(page_no))
  return ParsedDocument(paper_id=paper_id,document_sha256=digest(path),parser='pymupdf',parser_version=self.version,segments=tuple(segments),equations=tuple(equations),warnings=tuple(warnings))

class TesseractParser(BaseScientificParser):
 def parse(self,path,paper_id):
  if not shutil.which('tesseract'):raise PlatformError('OCR_NOT_CONFIGURED')
  segments=[]
  with tempfile.TemporaryDirectory() as tmp,fitz.open(path) as doc:
   if len(doc)>30:raise PlatformError('OCR_PAGE_BUDGET')
   for number,page in enumerate(doc,1):
    scale=min(2.,(10000000/max(1,page.rect.width*page.rect.height))**.5);image=Path(tmp)/f'{number}.png';page.get_pixmap(matrix=fitz.Matrix(scale,scale)).save(image)
    run=subprocess.run(['tesseract',str(image),'stdout','-l','eng','--psm','3'],capture_output=True,timeout=45)
    if run.returncode:raise PlatformError('OCR_FAILED')
    text=run.stdout.decode('utf-8').strip();segments.append(Segment(segment_id=f'ocr:p{number}',text=text,page=number,section=None,kind='ocr_text',bbox=(0.,0.,float(page.rect.width),float(page.rect.height)),source_path=str(number)+'.png'))
  return ParsedDocument(paper_id=paper_id,document_sha256=digest(path),parser='tesseract',parser_version='tesseract-eng-1',segments=tuple(segments),warnings=('OCR_TEXT_UNVERIFIED','MATHEMATICAL_TEXT_REQUIRES_REVIEW'))

class GrobidParser(BaseScientificParser):
 def __init__(self,url=None):self.url=url
 @staticmethod
 def parse_tei(xml,paper_id,document_hash):
  if len(xml)>16000000 or '<!DOCTYPE' in xml.upper() or '<!ENTITY' in xml.upper():raise PlatformError('UNSAFE_XML')
  try:root=ET.fromstring(xml)
  except ET.ParseError:raise PlatformError('INVALID_TEI') from None
  ns={'t':'http://www.tei-c.org/ns/1.0'};segments=[];equations=[]
  for i,node in enumerate(root.findall('.//t:body//t:p',ns)+root.findall('.//t:body//t:formula',ns)):
   text=''.join(node.itertext());is_formula=node.tag.endswith('formula');page=None
   coords=node.get('coords','').split(',')
   try:page=int(coords[0]) if coords and coords[0] else None
   except ValueError:pass
   sid='tei:'+str(i);segments.append(Segment(segment_id=sid,text=text,page=page,section=None,kind='formula' if is_formula else 'paragraph',source_path='TEI/'+sid))
   if is_formula:equations.append(Equation(text=text,latex=node.text if node.get('type')=='latex' else None,number=node.get('n'),context_segment_ids=(sid,)))
  return ParsedDocument(paper_id=paper_id,document_sha256=document_hash,parser='grobid',parser_version='tei-adapter-1',segments=tuple(segments),equations=tuple(equations),warnings=('EXTERNAL_PARSER_MAPPING_REQUIRES_REVIEW',))
 def parse(self,path,paper_id):
  if not self.url:raise PlatformError('GROBID_NOT_CONFIGURED')
  try:
   with httpx.Client(timeout=90,follow_redirects=False) as c,Path(path).open('rb') as f:r=c.post(self.url.rstrip('/')+'/api/processFulltextDocument',files={'input':(Path(path).name,f,'application/pdf')},data={'teiCoordinates':'p,formula,head,figure'})
   if r.status_code!=200:raise PlatformError('GROBID_SERVICE_ERROR',status=r.status_code)
   return self.parse_tei(r.text,paper_id,digest(path))
  except httpx.HTTPError:raise PlatformError('GROBID_UNAVAILABLE') from None

class DoclingParser(BaseScientificParser):
 def __init__(self,command=None):self.command=command
 @staticmethod
 def parse_json(data,paper_id,document_hash):
  segments=[];equations=[]
  for i,item in enumerate(data.get('texts',[])):
   prov=(item.get('prov') or [{}])[0];box=prov.get('bbox');bbox=None
   if box and all(k in box for k in ['l','t','r','b']):bbox=tuple(float(box[k]) for k in ['l','t','r','b'])
   text=item.get('text','');sid='docling:'+str(i);kind=str(item.get('label','paragraph'))
   segments.append(Segment(segment_id=sid,text=text,page=prov.get('page_no'),section=None,kind=kind,bbox=bbox,source_path=item.get('self_ref')))
   if kind=='formula':equations.append(Equation(text=text,latex=item.get('latex'),context_segment_ids=(sid,)))
  return ParsedDocument(paper_id=paper_id,document_sha256=document_hash,parser='docling',parser_version='docling-json-adapter-1',segments=tuple(segments),equations=tuple(equations),warnings=('EXTERNAL_PARSER_MAPPING_REQUIRES_REVIEW',))
 def parse(self,path,paper_id):
  command=self.command or shutil.which('docling')
  if not command:raise PlatformError('DOCLING_NOT_CONFIGURED')
  with tempfile.TemporaryDirectory() as tmp:
   run=subprocess.run([command,str(Path(path).resolve()),'--to','json','--output',tmp],capture_output=True,timeout=180)
   if run.returncode:raise PlatformError('DOCLING_FAILED')
   files=list(Path(tmp).glob('*.json'))
   if len(files)!=1 or files[0].stat().st_size>16000000:raise PlatformError('DOCLING_OUTPUT_INVALID')
   return self.parse_json(json.loads(files[0].read_text()),paper_id,digest(path))

def align_documents(primary,secondary):
 if primary.document_sha256!=secondary.document_sha256:raise PlatformError('PARSER_DOCUMENT_HASH_MISMATCH')
 mappings=[];conflicts=[];used=set()
 norm=lambda s:re.sub(r'\s+',' ',s).strip()
 candidates=[s for s in primary.segments if s.text.strip() and s.kind not in EXCLUDED]
 for s in secondary.segments:
  ranked=sorted(((SequenceMatcher(None,norm(s.text),norm(p.text)).ratio(),p) for p in candidates),key=lambda x:x[0],reverse=True)
  if ranked and ranked[0][0]>=.88 and ranked[0][1].segment_id not in used:
   score,p=ranked[0];used.add(p.segment_id);mappings.append({'secondary_segment':s.segment_id,'primary_segment':p.segment_id,'page':p.page,'score':score})
  else:conflicts.append('UNALIGNED_OR_DUPLICATE:'+s.segment_id)
 return {'mappings':mappings,'conflicts':conflicts,'merged_text':False}

class ParserRouter:
 def __init__(self,*,grobid_url=None,docling_command=None):self.grobid=GrobidParser(grobid_url);self.docling=DoclingParser(docling_command)
 def parse(self,path,paper_id):
  try:primary=PyMuPDFParser().parse(path,paper_id)
  except Exception as e:
   # Only known no-text documents are eligible for OCR, never arbitrary corrupt PDFs.
   from contracts import ContractError,ErrorKind
   if isinstance(e,ContractError) and e.error_kind==ErrorKind.NEEDS_OCR:primary=TesseractParser().parse(path,paper_id)
   else:raise
  external={}
  for name,parser in [('grobid',self.grobid),('docling',self.docling)]:
   if (name=='grobid' and not self.grobid.url) or (name=='docling' and not self.docling.command and not shutil.which('docling')):
    external[name]={'status':'NOT EXECUTED','reason':'NOT_CONFIGURED'};continue
   try:
    doc=parser.parse(path,paper_id);external[name]={'status':'EXECUTED','alignment':align_documents(primary,doc)}
   except PlatformError as e:external[name]={'status':'FAILED','error':e.safe()}
  if all(external[n]['status']=='EXECUTED' for n in ('grobid','docling')):external['dual_parser']={'status':'EXECUTED'}
  else:external['dual_parser']={'status':'NOT EXECUTED','reason':'BOTH_REAL_PARSERS_REQUIRED'}
  return primary,external

class XMLParser(BaseScientificParser):
 """JATS text with source element paths. No fabricated PDF page numbers."""
 def parse(self,path,paper_id):
  data=Path(path).read_bytes()
  if len(data)>16000000 or b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():raise PlatformError('UNSAFE_XML')
  try:root=ET.fromstring(data)
  except ET.ParseError:raise PlatformError('INVALID_XML_FORMAT') from None
  segments=[];equations=[]
  def walk(node,section=None,kind='front_matter',route='article'):
   local=node.tag.split('}')[-1]
   if local in {'ref-list','ack'}:kind='references' if local=='ref-list' else 'acknowledgements'
   if local=='caption':kind='caption'
   if local=='sec':
    title=next((c for c in node if c.tag.split('}')[-1]=='title'),None)
    if title is not None:section=''.join(title.itertext());kind=heading(section) or 'unknown'
   if local in {'p','disp-formula','inline-formula','table'}:
    text=''.join(node.itertext());sid='xml:'+str(len(segments));segments.append(Segment(segment_id=sid,text=text,page=None,section=section,kind='formula' if local.endswith('formula') else 'table' if local=='table' else kind,source_path=route))
    if local.endswith('formula'):
     latex=next((''.join(c.itertext()) for c in node.iter() if c.tag.split('}')[-1]=='tex-math'),None)
     equations.append(Equation(text=text,latex=latex,context_segment_ids=(sid,)))
    return
   for i,c in enumerate(node):walk(c,section,kind,route+'/'+c.tag.split('}')[-1]+'['+str(i)+']')
  walk(root)
  return ParsedDocument(paper_id=paper_id,document_sha256=digest(path),parser='JATS-XML',parser_version='jats-1',segments=tuple(segments),equations=tuple(equations),warnings=('XML_PAGE_MAPPING_UNAVAILABLE',))
