"""Test-only disabled instances; no source mutation and no production flags.

Length off retains an overlong field: a policy comparison, not bad evidence.
Slice/evidence off accepts corrupt evidence: destructive mutation checks.
"""
import sys
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'src'),str(Path(__file__).resolve().parents[1]/'acceptance')]
from contracts import ContractError
from extractors.composite import CompositeExtractor
from m14_extraction_validation import wrong_candidates_for_testing

def main():
    failures=0
    for name,(paper,view,candidate) in wrong_candidates_for_testing().items():
        enabled_for_testing=CompositeExtractor(view=view)
        disabled_for_testing=CompositeExtractor(view=view,**{f'enable_{name}_check':False})
        try:
            unchecked=disabled_for_testing.validate_candidate(paper,candidate)
            if name=='length':
                checked=enabled_for_testing.validate_candidate(paper,candidate)
                assert len(unchecked.methods)>3000 and checked.methods==''
                assert 'methods_fallback_truncated' in checked.warnings
            else:
                try:enabled_for_testing.validate_candidate(paper,candidate)
                except ContractError:pass
                else:raise AssertionError('enabled check failed to reject')
        except Exception as exc:print(f'FAIL {name}: {type(exc).__name__}');failures+=1
        else:print(f'PASS {name}: '+('disabled retains / enabled downgrades' if name=='length' else 'disabled accepts corrupt evidence / enabled rejects'))
    print(f'MUTATION SUMMARY: {3-failures} passed, {failures} failed')
    return int(bool(failures))
if __name__=='__main__':raise SystemExit(main())
