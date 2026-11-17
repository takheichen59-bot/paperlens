from pathlib import Path
import json,re
class VenueRegistry:
 def __init__(self,path=None):
  self.path=Path(path) if path else Path(__file__).with_name('venues.json')
  self.data=json.loads(self.path.read_text() if self.path.exists() else Path(__file__).with_name('venues.json').read_text())
 def match(self,name):
  norm=lambda s:' '+re.sub(r'\W+',' ',s.casefold()).strip()+' '
  value=norm(name or '')
  return tuple(v for v in self.data['venues'] if any(norm(a) in value for a in [v['name'],*v['aliases']]))
 def add(self,name,domain,aliases=()):
  if not name.strip() or len(name)>300:raise ValueError('Invalid venue')
  self.data['venues'].append({'id':re.sub(r'\W+','_',name.casefold()),'name':name,'domain':domain,'aliases':list(aliases),'curation':'User-maintained'})
  tmp=self.path.with_suffix('.part');tmp.write_text(json.dumps(self.data,ensure_ascii=False,indent=2)+'\n');tmp.replace(self.path)
