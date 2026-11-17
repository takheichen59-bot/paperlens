"""Exports from one transactional snapshot; identifiers and evidence retained."""
from io import StringIO,BytesIO
import csv,json,zipfile
from xml.sax.saxutils import escape
from .models import ScientificRecord

def safe_cell(value):
 text=value if isinstance(value,str) else json.dumps(value,ensure_ascii=False)
 return "'"+text if text.startswith(('\t','\r')) or text.lstrip().startswith(('=','+','-','@')) else text

def encode_export(rows,format):
 if format=='jsonl':return ('\n'.join(json.dumps(r,ensure_ascii=False,allow_nan=False) for r in rows)+'\n').encode(),'application/x-ndjson'
 # Spreadsheets keep readable columns alongside the complete nested source.
 if format in {'csv','xlsx'}:
  def readable(row):
   if 'paper' not in row:return row
   p=row['paper'];r=row.get('extraction') or {}
   text=lambda name:'\n'.join(c['text'] for c in r.get(name,[]))
   return {'paper_id':p['paper_id'],'doi':p.get('doi') or '', 'title':p['title'],'source_url':p.get('source_url') or '',
    'extraction_status':r.get('execution_status','NOT_EXTRACTED'),'methodology':text('methodology'),'conclusions':text('conclusions'),'results':text('results'),**row}
  rows=[readable(row) for row in rows]
 keys=list(dict.fromkeys(k for r in rows for k in r))
 if format=='csv':
  out=StringIO(newline='');writer=csv.writer(out);writer.writerow(keys)
  for r in rows:writer.writerow([safe_cell(r.get(k,'')) for k in keys])
  return out.getvalue().encode('utf-8-sig'),'text/csv; charset=utf-8'
 if format=='xlsx':
  def col(n):
   out=''
   while n:n,k=divmod(n-1,26);out=chr(65+k)+out
   return out
  table=[keys]+[[safe_cell(r.get(k,'')) for k in keys] for r in rows];xml=['<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>']
  for i,row in enumerate(table,1):
   xml.append('<row r="'+str(i)+'">')
   for j,value in enumerate(row,1):
    text=''.join(c for c in str(value)[:32767] if ord(c)>=32 or c in '\n\r\t');xml.append('<c r="'+col(j)+str(i)+'" t="inlineStr"><is><t xml:space="preserve">'+escape(text)+'</t></is></c>')
   xml.append('</row>')
  xml.append('</sheetData></worksheet>');out=BytesIO()
  with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
   z.writestr('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>')
   z.writestr('_rels/.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
   z.writestr('xl/workbook.xml','<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Research" sheetId="1" r:id="rId1"/></sheets></workbook>')
   z.writestr('xl/_rels/workbook.xml.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>');z.writestr('xl/worksheets/sheet1.xml',''.join(xml))
  return out.getvalue(),'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
 raise ValueError('format must be jsonl, csv or xlsx')
