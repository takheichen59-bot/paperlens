"""Synthetic PDF fixtures generated offline using the parser dependency itself."""
from pathlib import Path
import fitz


def make_pdf(path,pages):
    doc=fitz.open()
    for items in pages:
        p=doc.new_page(width=600,height=800)
        from parsers.heading_config import HEADINGS
        for x,y,text in items:p.insert_text((x,y),text,fontsize=11,fontname='hebo' if text.lower() in HEADINGS else 'helv')
    doc.save(path);doc.close();return Path(path)


def materials_pdf(path,material='Titanium dioxide',methods=True,conclusion=True):
    lines=['Synthetic materials paper','Abstract','A study of a protective coating.','Materials and Methods']
    if methods:lines.append(material+' was prepared by hydrothermal synthesis at 180 C.')
    else:lines[-1]='Introduction';lines.append('The research question concerns coating behavior.')
    lines+=['Results','The measured resistance increased by 20 percent.']
    if conclusion:lines+=['Conclusions','The coating improved corrosion resistance.']
    lines+=['References','1. Smith. Lithium chloride synthesis, 2010.']
    return make_pdf(path,[[(50,60+i*38,text) for i,text in enumerate(lines)]])
