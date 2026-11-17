import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from _support import run_cases
from contracts import *
from parsers.sections import SectionIdentifier,eligible_blocks as _eligible
import hashlib,json,tempfile,asyncio
from storage import Database,TaskRepository
from pipeline import PaperPipeline
from _pipeline_fixtures import metadata,LocalFetcher
from _pdf_fixtures import materials_pdf
from _pdf_fixtures import make_pdf


def case_two_column_left_first():
    from parsers.sections import StructuredPDFParser
    from extractors.composite import CompositeExtractor
    with tempfile.TemporaryDirectory() as d:
        path=make_pdf(Path(d)/'columns.pdf',[[(40,90,'Methods'),(330,90,'Conclusions'),
            (40,130,'Titanium dioxide was prepared by deposition.'),
            (330,130,'The coating improved resistance and stability.'),
            (40,170,'Films were heated and measured at 180 C.'),
            (330,170,'The resulting samples remained stable after testing.')]])
        p,v=StructuredPDFParser().parse_with_view(path)
        body=_eligible(p,v);ids=[b.block_id for b in body]
        left=[b.block_id for b in body if b.bbox[0]<300]
        right=[b.block_id for b in body if b.bbox[0]>=300]
        assert ids==left+right
        r=CompositeExtractor(view=v).extract(p)
        assert r.methods.index('Titanium')<r.methods.index('Films')
        assert r.conclusions.startswith('The coating') and 'prepared' not in r.conclusions
        assert 'improved' not in r.methods


def case_caption_separation():
    from parsers.sections import StructuredPDFParser
    from extractors.composite import CompositeExtractor
    with tempfile.TemporaryDirectory() as d:
        path=make_pdf(Path(d)/'caption.pdf',[[(40,90,'Methods'),(40,130,'Titanium dioxide was prepared at 180 C.'),
            (40,170,'FIG. 2. DFT simulations predict a stable coating.'),(40,210,'Conclusions'),
            (40,250,'The coating improved corrosion resistance.')]])
        p,v=StructuredPDFParser().parse_with_view(path);r=CompositeExtractor(view=v).extract(p)
        caption=next(b for b in p.raw_blocks if b.text.startswith('FIG.'))
        assert 'caption_block:'+caption.block_id in p.warnings
        assert any(bid==caption.block_id for bid,_,_ in v.excluded)
        assert 'FIG.' not in r.methods+r.conclusions and 'DFT simulations' not in r.methods
        assert not any(s.block_id==caption.block_id for s in r.source_snippets)


def case_body_figure_reference():
    from parsers.sections import StructuredPDFParser
    from extractors.composite import CompositeExtractor
    with tempfile.TemporaryDirectory() as d:
        sentence='Samples were prepared as shown in Fig. 2 and heated at 180 C.'
        path=make_pdf(Path(d)/'inline.pdf',[[(40,90,'Methods'),(40,130,sentence),(40,180,'Conclusions'),(40,220,'The prepared coating remained stable.')]])
        p,v=StructuredPDFParser().parse_with_view(path)
        assert sentence in CompositeExtractor(view=v).extract(p).methods
        assert not any(w.startswith('caption_block:') for w in p.warnings)


def case_cross_page_continuation():
    from parsers.sections import StructuredPDFParser
    from extractors.composite import CompositeExtractor
    with tempfile.TemporaryDirectory() as d:
        a='Titanium dioxide was prepared and heated using a controlled'
        b='deposition protocol; samples were measured at 180 C.'
        path=make_pdf(Path(d)/'pages.pdf',[
            [(40,25,'Repeated Journal Header'),(40,100,'Methods'),(40,700,a),(290,780,'1')],
            [(40,25,'Repeated Journal Header'),(40,90,b),(40,160,'Conclusions'),
             (40,200,'The coating improved corrosion resistance.'),(290,780,'2')]])
        p,v=StructuredPDFParser().parse_with_view(path);r=CompositeExtractor(view=v).extract(p)
        assert r.methods==a+'\n\n'+b and 'Journal' not in r.methods
        refs=[s for s in r.source_snippets if s.field==ExtractionField.METHODS]
        assert [s.page_start for s in refs]==[1,2]
        assert all(s.page_start==s.page_end for s in refs)
        raw={b.block_id:b for b in p.raw_blocks}
        assert all(raw[s.block_id].text[s.start_offset:s.end_offset]==s.text for s in refs)


def case_single_column_centered():
    from parsers.sections import StructuredPDFParser
    from extractors.composite import CompositeExtractor
    with tempfile.TemporaryDirectory() as d:
        path=make_pdf(Path(d)/'single.pdf',[[(40,90,'Methods'),(40,130,'Titanium dioxide was prepared and heated.'),
            (280,170,'Centered'),(40,210,'Samples were measured and then dried.'),(290,780,'1')]])
        p,v=StructuredPDFParser().parse_with_view(path)
        body=_eligible(p,v)
        assert [b.bbox[1] for b in body]==sorted(b.bbox[1] for b in body)
        r=CompositeExtractor(view=v).extract(p)
        assert r.methods.index('Titanium')<r.methods.index('Samples')
        assert not any('possible_multicolumn' in w for w in p.warnings)


def case_visual_adjacent_caption():
    from parsers.reading_order import is_caption
    b=TextBlock(block_id='visual-note',page_number=1,text='A short description below an image.',bbox=(40.,200.,250.,215.))
    assert is_caption(b,{('visual-note',0):{'after_visual':True,'bold':False}})
    assert not is_caption(b,{('visual-note',0):{'after_visual':False}})

def eligible_blocks(p):
    p,v=SectionIdentifier().identify_with_view(p)
    return _eligible(p,v)

def paper(lines):
    blocks=tuple(TextBlock(block_id=f'b{i}',page_number=1,text=t,bbox=None) for i,t in enumerate(lines))
    p=ParsedPaper(paper_id='p',pdf_hash='a'*64,pages=(PageText(page_number=1,text='\n'.join(lines)),),raw_blocks=blocks,cleaned_text='\n'.join(lines),sections=(),warnings=())
    return SectionIdentifier().identify(p)
def case_standard():
    p=paper(['Abstract','Overview','Methods','Measured samples','Conclusions','Summary','References','Lithium chloride cited'])
    assert [s.kind for s in p.sections]==[SectionKind.ABSTRACT,SectionKind.METHODS,SectionKind.CONCLUSIONS,SectionKind.REFERENCES]
    assert all('cited' not in b.text for b in eligible_blocks(p))
def case_numbered():
    p=paper(['2.1 Materials and Methods','Hydrothermal synthesis','3 Conclusions','Stable coating'])
    assert p.sections[0].kind==SectionKind.METHODS and p.sections[1].kind==SectionKind.CONCLUSIONS
def case_combined():
    p=paper(['Results and Discussion','Findings']);assert p.sections[0].kind==SectionKind.DISCUSSION
def case_body_words():
    p=paper(['We discuss methods and results in this paragraph.','This is not a heading.'])
    assert len(p.sections)==1 and p.sections[0].kind==SectionKind.UNKNOWN
def case_unknown_and_supplement():
    p=paper(['Untitled paper','Ordinary text']);assert 'sections_unknown' in p.warnings
    p=paper(['References','Cited material','Supplementary information','Extra data'])
    assert not eligible_blocks(p) and p.raw_blocks[-1].text=='Extra data'

def raw_paper(text):
    return ParsedPaper(paper_id='p',pdf_hash='a'*64,pages=(PageText(page_number=1,text=text),),raw_blocks=(TextBlock(block_id='b',page_number=1,text=text,bbox=None),),cleaned_text=text,sections=(),warnings=())
def case_reference_leak():
    from extractors import ChemicalExtractor
    p,v=SectionIdentifier().identify_with_view(raw_paper('Methods\nSamples were prepared.\nReferences\nTiO2 NaCl H2O graphene lithium chloride'))
    assert ChemicalExtractor(view=v).extract(p).chemicals==()
def case_funding_leak():
    from extractors import ChemicalExtractor
    p,v=SectionIdentifier().identify_with_view(raw_paper('Conclusions\nThe material was stable.\nFunding\nDOE DE-SC0012704; graphene and TiO2.'))
    assert ChemicalExtractor(view=v).extract(p).chemicals==()
def case_acknowledgement_title():
    p,v=SectionIdentifier().identify_with_view(raw_paper('Acknowledgements\nDE-SC0012704'))
    assert p.sections[0].kind==SectionKind.REFERENCES and p.sections[0].title=='Acknowledgements'
    assert not _eligible(p,v)
def case_raw_unchanged_coverage():
    before=raw_paper('Methods\nGraphene was deposited.\nAcknowledgements\nDE-SC0012704')
    digest=hashlib.sha256(json.dumps([b.model_dump(mode='json') for b in before.raw_blocks]).encode()).hexdigest()
    p,v=SectionIdentifier().identify_with_view(before)
    assert p.raw_blocks==before.raw_blocks and len(p.raw_blocks)==1
    assert hashlib.sha256(json.dumps([b.model_dump(mode='json') for b in p.raw_blocks]).encode()).hexdigest()==digest
    intervals=sorted((a,b) for sec in v.sections for bid,a,b in sec.spans)
    assert intervals[0][0]==0 and intervals[-1][1]==len(before.raw_blocks[0].text)
    assert all(x[1]==y[0] for x,y in zip(intervals,intervals[1:]))
def case_refs_and_ack_coexist():
    p,v=SectionIdentifier().identify_with_view(raw_paper('References\nTiO2 cited.\nAcknowledgements\nDE-SC0012704'))
    assert [(s.kind,s.title) for s in p.sections]==[(SectionKind.REFERENCES,'References'),(SectionKind.REFERENCES,'Acknowledgements')]
    assert not _eligible(p,v)
def case_old_cache_reparsed():
    from parsers.sections import StructuredPDFParser
    with tempfile.TemporaryDirectory() as d,Database(Path(d)/'db') as db:
        path=materials_pdf(Path(d)/'p.pdf');f=LocalFetcher({1:path});pipeline=PaperPipeline(db,Path(d)/'cache',f)
        asyncio.run(pipeline.run('2401.00001'))
        cache=pipeline.checkpoints.path(metadata().paper_id,Stage.PARSE)
        data=json.loads(cache.read_text());assert data['section_view']
        del data['section_view'];del data['section_view_checksum'];cache.write_text(json.dumps(data))
        asyncio.run(pipeline.run('2401.00001'))
        assert TaskRepository(db).get_current(metadata().paper_id,Stage.PARSE).attempts==2
        data=json.loads(cache.read_text());view=json.loads(data['section_view'])
        assert view['sections'] and view['pdf_hash']==json.loads(data['payload'])['pdf_hash']
        assert view['parser_version']==pipeline.parser.version
        from hashlib import sha256
        expected_attempts=2
        for key in ('pdf_hash','parser_version'):
            data=json.loads(cache.read_text());view=json.loads(data['section_view'])
            view[key]='wrong'
            payload=json.dumps(view,sort_keys=True)
            data['section_view']=payload;data['section_view_checksum']=sha256(payload.encode()).hexdigest()
            cache.write_text(json.dumps(data))
            asyncio.run(pipeline.run('2401.00001'));expected_attempts+=1
            assert TaskRepository(db).get_current(metadata().paper_id,Stage.PARSE).attempts==expected_attempts


def case_roman_headers():
    from parsers.pdf import font_is_bold
    assert font_is_bold("CMBX10",4) and font_is_bold("NimbusRomNo9L-Medi",4)
    assert not font_is_bold("Times-Roman",4)
    from parsers.sections import StructuredPDFParser
    import fitz
    with tempfile.TemporaryDirectory() as d:
        path=Path(d)/'roman.pdf';doc=fitz.open();page=doc.new_page()
        for y,text,font in [(70,'II. Experimental Methods','hebo'),(110,'Samples were prepared and heated.','helv'),(160,'VI. Methods','hebo'),(200,'Films were washed and dried.','helv'),(250,'I. The results show...','helv')]:
            page.insert_text((50,y),text,fontname=font,fontsize=11)
        doc.save(path);doc.close();p,v=StructuredPDFParser().parse_with_view(path)
        assert [sec.title for sec in p.sections]==['II. Experimental Methods','VI. Methods']
        assert all('The results' not in sec.title for sec in p.sections)
def case_calculation_details():
    p=paper(['2 Calculation details','We performed simulations.','Computational details','Further calculations.'])
    assert len(p.sections)==2 and all(sec.kind==SectionKind.METHODS for sec in p.sections)
def case_nested_numbering():
    p=paper(['1.2.3 Experimental section','Samples were heated.'])
    assert p.sections[0].kind==SectionKind.METHODS

if __name__ == "__main__":
    raise SystemExit(run_cases(['case_standard','case_numbered','case_combined','case_body_words','case_unknown_and_supplement','case_reference_leak','case_funding_leak','case_acknowledgement_title','case_raw_unchanged_coverage','case_refs_and_ack_coexist','case_old_cache_reparsed','case_roman_headers','case_calculation_details','case_nested_numbering','case_two_column_left_first','case_caption_separation','case_body_figure_reference','case_cross_page_continuation','case_single_column_centered','case_visual_adjacent_caption'],globals()))
