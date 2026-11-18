"""Derive a small OFL font for public synthetic UI tests, never from paper contents."""
import argparse,hashlib
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools import subset
p=argparse.ArgumentParser();p.add_argument('--font',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();root=Path(__file__).resolve().parents[2]
font=TTFont(a.font,recalcTimestamp=False);characters=set(range(32,127))|set(range(0xa0,0x250))|set(range(0x370,0x400))|set(range(0x2000,0x2300))|{0x1f100,0x2dc}
for folder in [root/'website/web_assets',root/'website/fixtures',root/'tests/browser']:
 for f in folder.rglob('*'):
  if f.suffix in {'.js','.mjs','.py','.html'} and 'vendor' not in f.parts:characters.update(ord(c) for c in f.read_text())
characters&=set(font.getBestCmap());opts=subset.Options();opts.layout_features=[];opts.name_IDs=['*'];opts.notdef_glyph=True;opts.recalc_timestamp=False
sub=subset.Subsetter(options=opts);sub.populate(unicodes=sorted(characters));sub.subset(font)
if 'GSUB' in font:del font['GSUB']
a.output.parent.mkdir(parents=True,exist_ok=True);font.save(a.output);raw=a.output.read_bytes();print({'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'characters':len(font.getBestCmap())})
