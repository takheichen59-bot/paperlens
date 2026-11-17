"""Resource-limited PDF structure probe. Executed in a separate process."""
import sys,json
try:
 try:
  import resource
  resource.setrlimit(resource.RLIMIT_AS,(1536*1024*1024,1536*1024*1024));resource.setrlimit(resource.RLIMIT_CPU,(40,40))
 except ImportError:pass
 import pymupdf as fitz
 with open(sys.argv[1],'rb') as header:
  if not header.read(8).startswith(b'%PDF-'):raise ValueError()
 fitz.TOOLS.mupdf_display_errors(False);fitz.TOOLS.mupdf_display_warnings(False)
 with fitz.open(sys.argv[1]) as doc:
  if not doc.is_pdf or doc.needs_pass or not 0<len(doc)<=3000:raise ValueError()
  chars=0
  for page in doc:
   chars+=len(page.get_text())
   if chars>12000000:raise ValueError()
  print(json.dumps({'pages':len(doc),'characters':chars,'needs_ocr':chars<200}))
except Exception:
 print(json.dumps({'code':'PDF_CORRUPTED'}));raise SystemExit(1)
