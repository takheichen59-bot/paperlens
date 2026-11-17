"""Run module acceptance and validate failure consumers without count inflation."""
from pathlib import Path
import argparse,json,re,subprocess,sys
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'src'))
from exports import (parse_failure_line,open_current_snapshot,read_current_results,
    read_current_warnings_by_severity,read_current_failures,is_warning_classification_error)
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--results',type=Path,help='Also verify a published export snapshot')
args=parser.parse_args()
failures=[];checks=0
scripts=sorted((root/'acceptance').glob('m[0-2][0-9]_*.py'))
if [p.name[:3] for p in scripts]!=[f'm{i:02d}' for i in range(1,21)]:
    print('FAIL: module acceptance scripts missing or duplicated');raise SystemExit(1)
repairs=sorted((root/'acceptance').glob('repair_*.py'))
scripts+=repairs
for script in scripts:
    print('\n$ python '+str(script.relative_to(root)),flush=True)
    result=subprocess.run([sys.executable,str(script)],cwd=root,text=True,capture_output=True)
    print(result.stdout,end='',flush=True);print(result.stderr,end='',file=sys.stderr,flush=True)
    match=re.search(r'SUMMARY: (\d+) passed, (\d+) failed',result.stdout)
    if match:checks+=int(match[1])+int(match[2])
    if result.returncode or not match:failures.append(script.name)
for path in (root/'examples').glob('*failures*.jsonl'):
    for line in path.read_text().splitlines():
        record=parse_failure_line(json.loads(line))
        if is_warning_classification_error(record):print('Example contains an internal classification failure')
if args.results:
    with open_current_snapshot(args.results) as snapshot:
        rows=read_current_results(args.results,snapshot=snapshot)
        warnings=read_current_warnings_by_severity(args.results,snapshot=snapshot)
        errors=read_current_failures(args.results,snapshot=snapshot)
        internal={r.paper_id for r in errors if is_warning_classification_error(r)}
        print(f'Published snapshot: version={snapshot.version_id} published_at={snapshot.published_at} records={len(rows)} informational={sum(len(w.informational) for w in warnings)} blocking={sum(len(w.blocking) for w in warnings)} internal_classification_papers={len(internal)}')
mutation=subprocess.run([sys.executable,str(root/'scripts/verify_m14_checks.py')],cwd=root)
if mutation.returncode:failures.append('M14 check switches')
resume=subprocess.run([sys.executable,str(root/'scripts/verify_resume.py')],cwd=root)
if resume.returncode:failures.append('SIGKILL/resume')
print(f'\nALL MODULES: '+(f'PASS (20 module scripts; {len(repairs)} repair scripts; {checks} active checks; historical skips excluded)' if not failures else 'FAIL: '+', '.join(failures)))
raise SystemExit(1 if failures else 0)
