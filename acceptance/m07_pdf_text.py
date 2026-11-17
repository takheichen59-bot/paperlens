import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from _support import run_cases
import tempfile
from parsers import PDFParser
from contracts import *
from _pdf_fixtures import make_pdf

def case_single_column():
    with tempfile.TemporaryDirectory() as d:
        p=PDFParser().parse(make_pdf(Path(d)/'one.pdf',[[(50,70,'Titanium dioxide coating.'),(50,120,'Methods')]]))
        assert 'Titanium dioxide' in p.cleaned_text and len(p.pages)==1
        assert p.raw_blocks[0].page_number==1 and p.raw_blocks[0].bbox is not None
def case_multicolumn():
    with tempfile.TemporaryDirectory() as d:
        p=PDFParser().parse(make_pdf(Path(d)/'two.pdf',[[(40,70,'Left column.'),(330,70,'Right column.')]]))
        assert 'Left column.' in p.cleaned_text and 'Right column.' in p.cleaned_text
        assert any('multicolumn' in w for w in p.warnings)
def case_multiple_pages():
    with tempfile.TemporaryDirectory() as d:
        p=PDFParser().parse(make_pdf(Path(d)/'multi.pdf',[[(50,70,'Page one text')],[(50,70,'Page two text')]]))
        assert [page.page_number for page in p.pages]==[1,2]
        assert len({b.block_id for b in p.raw_blocks})==len(p.raw_blocks)
def case_corrupted():
    with tempfile.TemporaryDirectory() as d:
        path=Path(d)/'broken.pdf';path.write_bytes(b'not a PDF')
        try:PDFParser().parse(path)
        except ContractError as e:assert e.error_kind==ErrorKind.PDF_CORRUPTED
        else:raise AssertionError('bad PDF accepted')
def case_scan():
    import fitz
    with tempfile.TemporaryDirectory() as d:
        path=Path(d)/'scan.pdf';doc=fitz.open();page=doc.new_page();page.draw_rect(fitz.Rect(20,20,80,80),fill=(0,0,0));doc.save(path);doc.close()
        try:PDFParser().parse(path)
        except ContractError as e:assert e.error_kind==ErrorKind.NEEDS_OCR
        else:raise AssertionError('image-only accepted')

def case_single_column_centered_numbers():
    from parsers.sections import StructuredPDFParser
    from parsers.pdf import is_page_number
    with tempfile.TemporaryDirectory() as d:
        path=make_pdf(Path(d)/'centered.pdf',[[(50,100,'This is a single column body paragraph.'),(295,400,'123'),(295,780,'2')]])
        paper,view=StructuredPDFParser().parse_with_view(path)
        assert not any('multicolumn' in w for w in paper.warnings)
        assert '123' in paper.cleaned_text
        assert is_page_number('2',(295.,760.,305.,770.),600,800)
        assert not is_page_number('123',(295.,390.,315.,405.),600,800)
        assert not is_page_number('2',(50.,760.,550.,770.),600,800)
        path=make_pdf(Path(d)/'different-heights.pdf',[[(40,70,'Short left ending'),(400,170,'Right-side fragment')]])
        assert not any('multicolumn' in w for w in PDFParser().parse(path).warnings)

if __name__ == "__main__":
    raise SystemExit(run_cases(['case_single_column', 'case_multicolumn', 'case_multiple_pages', 'case_corrupted', 'case_scan','case_single_column_centered_numbers'], globals()))
