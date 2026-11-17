"""Page/block text extraction with original coordinates and stable block IDs."""
from hashlib import sha256
from pathlib import Path
try:
    import pymupdf as fitz
except ImportError:  # Compatibility with the earliest allowed PyMuPDF 1.24 releases.
    import fitz
import re
from contracts import *


BOLD_FONT_TOKENS=('bold','cmbx','cmssbx','-medi','-demi','semibold','black')
def font_is_bold(font,flags):
    return bool(flags&16) or any(token in font.lower() for token in BOLD_FONT_TOKENS)


def is_page_number(text,bbox,width,height):
    if not bbox or not re.fullmatch(r'\s*\d+\s*',text):return False
    x0,y0,x1,y1=bbox
    return x1-x0<width*.30 and (y1<=height*.08 or y0>=height*.92)


class PDFParser(BaseParser):
    @property
    def version(self):return 'pymupdf-blocks-layout-v4'
    def parse(self,pdf_path:Path):
        path=Path(pdf_path)
        try:
            pages=[];blocks=[];warnings=[]
            with fitz.open(path) as doc:
                if doc.needs_pass:raise ContractError(Stage.PARSE,ErrorKind.PDF_CORRUPTED,False)
                for index,page in enumerate(doc,1):
                    text=page.get_text('text',sort=True)
                    pages.append(PageText(page_number=index,text=text))
                    if not text.strip():warnings.append(f'page_{index}_no_text')
                    for n,b in enumerate(page.get_text('dict',sort=True)['blocks']):
                        if b.get('type')!=0:continue
                        value='\n'.join(''.join(span['text'] for span in line['spans']) for line in b['lines'])
                        if value.strip():blocks.append(TextBlock(block_id=f'p{index}-b{n}',page_number=index,text=value,bbox=tuple(float(x) for x in b['bbox'])))
                    lines=[line for block in page.get_text('dict')['blocks'] if block.get('type')==0 for line in block['lines']]
                    lines=[line for line in lines if not is_page_number(''.join(s['text'] for s in line['spans']),line['bbox'],page.rect.width,page.rect.height)]
                    left=[line for line in lines if line['bbox'][0]<page.rect.width*.45 and line['bbox'][2]<page.rect.width*.55]
                    right=[line for line in lines if line['bbox'][0]>page.rect.width*.45 and line['bbox'][2]>page.rect.width*.55]
                    pairs=[(l,r) for l in left for r in right
                        if len(''.join(s['text'] for s in l['spans']).strip())>=6
                        and len(''.join(s['text'] for s in r['spans']).strip())>=6
                        and l['bbox'][2]+page.rect.width*.03<r['bbox'][0]
                        and min(l['bbox'][3],r['bbox'][3])-max(l['bbox'][1],r['bbox'][1])
                            >.5*min(l['bbox'][3]-l['bbox'][1],r['bbox'][3]-r['bbox'][1])]
                    if pairs:warnings.append(f'page_{index}_possible_multicolumn')
            if not any(p.text.strip() for p in pages):raise ContractError(Stage.PARSE,ErrorKind.NEEDS_OCR,False)
            return ParsedPaper(paper_id='local:'+sha256(path.read_bytes()).hexdigest(),pdf_hash=sha256(path.read_bytes()).hexdigest(),pages=tuple(pages),raw_blocks=tuple(blocks),cleaned_text='\n\n'.join(b.text for b in blocks),sections=(),warnings=tuple(warnings))
        except ContractError:raise
        except (OSError,RuntimeError,ValueError) as exc:
            raise ContractError(Stage.PARSE,ErrorKind.PDF_CORRUPTED,False,cause=exc) from exc

    def layout_hints(self,pdf_path):
        """Transient font/page hints keyed by (original block ID, raw line offset)."""
        from collections import Counter
        hints={}
        with fitz.open(pdf_path) as doc:
            font_counts=Counter()
            for page in doc:
                for b in page.get_text('dict')['blocks']:
                    if b.get('type')==0:
                        for line in b['lines']:
                            for s in line['spans']:font_counts[round(s['size'],1)]+=len(s['text'])
            body_size=font_counts.most_common(1)[0][0] if font_counts else 10.
            for index,page in enumerate(doc,1):
                visuals=[tuple(x['bbox']) for x in page.get_image_info()]
                # Table geometry is optional; missing detection never fabricates a table.
                if len(page.get_drawings())>=8:
                    try:
                        from contextlib import redirect_stdout
                        from io import StringIO
                        with redirect_stdout(StringIO()):tables=page.find_tables().tables
                        visuals.extend(tuple(t.bbox) for t in tables)
                    except (AttributeError,RuntimeError,ValueError):pass
                for n,b in enumerate(page.get_text('dict',sort=True)['blocks']):
                    if b.get('type')!=0:continue
                    offset=0
                    for line in b['lines']:
                        text=''.join(s['text'] for s in line['spans'])
                        hints[(f'p{index}-b{n}',offset)]={'bold':any(font_is_bold(s.get('font',''),s.get('flags',0)) for s in line['spans']),
                            'size':max((s['size'] for s in line['spans']),default=body_size),'body_size':body_size,
                            'bbox':tuple(line['bbox']),'page_width':page.rect.width,'page_height':page.rect.height,
                            'independent':True,'line_start':True,
                            'after_visual':any(0<=line['bbox'][1]-v[3]<=18 and min(line['bbox'][2],v[2])-max(line['bbox'][0],v[0])>min(line['bbox'][2]-line['bbox'][0],v[2]-v[0])*.5 for v in visuals)}
                        offset+=len(text)+1
        return hints
