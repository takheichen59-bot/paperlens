"""Regression checks for the reported failure mechanisms, not scientific accuracy."""
import copy
import unittest
from types import SimpleNamespace
from research.reading import build_reading,validate_reading,normalize_text,sentences,complete_sentence,scientific_title
from research.attribution import numeric_role
from parsers.reading_order import ordered_blocks


def record(blocks):
    return {'id':'synthetic-reading','paper_id':'synthetic-reading','pdf_hash':'a'*64,
        'meta':{'title':'Cr impurities in beta-Ga2O3 — SYNTHETIC'},'materials':[],'methods':'','findings':'','conclusions':'',
        'raw_blocks':[{'block_id':str(i),'page':page,'text':text,'bbox':box} for i,(page,text,box) in enumerate(blocks)],
        'eligible_ranges':[{'block_id':str(i),'start':0,'end':len(text),'section_kind':'unknown'} for i,(_,text,_) in enumerate(blocks)]}


class ReadingQualityTests(unittest.TestCase):
    def test_decimal_unit_and_citation_boundaries(self):
        text='The spectra were measured at 4.2 K using a 532 nm source. We observed a synthetic feature.12 Another feature was absent.'
        values=[text[a:z] for a,z in sentences(text)]
        self.assertEqual(len(values),3);self.assertIn('4.2 K',values[0]);self.assertTrue(all(complete_sentence(v) for v in values))
    def test_orphans_never_become_summary_sentences(self):
        for value in ['as a Fano anomaly in the line shape of the phonon mode.','temperature dependence of the frequency further corroborates our findings on the','The Raman data are shown in Fig.']:
            self.assertFalse(complete_sentence(value))
        self.assertTrue(complete_sentence('To study the synthetic sample, we used Raman spectroscopy.'))
    def test_normalization_keeps_chemical_hyphens_and_joins_known_split_words(self):
        self.assertEqual(normalize_text('net-\nworking and low-\ntemperature Cu-O bonds'),'networking and low-temperature Cu-O bonds')
    def test_cross_block_exact_sources_do_not_mutate_original_fields(self):
        r=record([(1,'😀 We used Raman spectroscopy to study electron-',(50,100,280,120)),(1,'phonon interactions in the synthetic samples.',(50,125,280,145))]);before=copy.deepcopy(r)
        c=build_reading(r);r['reading_card']=c;validate_reading(r)
        self.assertEqual(before,{k:v for k,v in r.items() if k!='reading_card'})
        s=next(x for x in c['evidence'] if 'Raman' in x['text']);self.assertEqual(s['pages'],[1]);self.assertEqual(len(s['parts']),2)
        for v in s['parts']:self.assertTrue(r['raw_blocks'][int(v['block_id'])]['text'][v['start']:v['end']])
    def test_wrong_page_or_source_part_is_rejected(self):
        r=record([(1,'We observed a complete synthetic result in the sample.',(50,100,280,120))]);r['reading_card']=build_reading(r)
        b=copy.deepcopy(r);b['reading_card']['evidence'][0]['parts'][0]['page']=9
        with self.assertRaises(ValueError):validate_reading(b)
        b=copy.deepcopy(r);b['reading_card']['evidence'][0]['parts'][0]['start']=-1
        with self.assertRaises(ValueError):validate_reading(b)
    def test_current_work_resets_earlier_background(self):
        role,_=numeric_role('Cr possesses a quartet ground-state spin and has an internal transition near 1.8 eV.','It is best known in ruby. We calculate its energetics from first principles.','introduction')
        self.assertEqual(role,'own_result')
        self.assertEqual(numeric_role('The results show a 97% rate.','In recent work, collaborators investigated catalysts.','introduction')[0],'cited_result')
    def test_sparse_column_order_does_not_read_tall_right_block_first(self):
        left=SimpleNamespace(block_id='left',page_number=1,text=('left column body\n'*18),bbox=(50,350,280,700))
        right=SimpleNamespace(block_id='right',page_number=1,text=('right column body\n'*30),bbox=(320,50,560,700))
        p=SimpleNamespace(raw_blocks=[right,left],warnings=[]);h={('left',0):{'page_width':600},('right',0):{'page_width':600}}
        ordered,_=ordered_blocks(p,h);self.assertEqual([b.block_id for b in ordered],['left','right'])
    def test_title_preserves_scientific_notation(self):
        self.assertEqual(scientific_title('Co$_x$NbSe$_2$'),'CoₓNbSe₂')
        self.assertEqual(scientific_title(r'$\beta$-Ga$_2$O$_3$'),'β-Ga₂O₃')
    def test_perspective_does_not_require_experimental_steps(self):
        r=record([(1,'We outline and discuss outstanding challenges for quantum matter and the development of theories.',(50,100,550,150))]);r['meta']['title']='Challenges in understanding Quantum Matter';c=build_reading(r)
        self.assertEqual(c['fields']['methods']['status'],'not_applicable');self.assertEqual(c['fields']['findings']['status'],'not_applicable');self.assertEqual(c['quality']['human_review'],'unreviewed')

if __name__=='__main__':unittest.main()
