"""Offline acceptance runner; cases are independent functions with assertions."""
def run_cases(names, namespace):
    assert names and len(set(names))==len(names)
    passed=0
    for name in names:
        try:
            namespace[name]()
        except Exception as exc:
            print(f'FAIL {name}: {type(exc).__name__}')
        else:
            passed+=1
            print(f'PASS {name}')
    print(f'SUMMARY: {passed} passed, {len(names)-passed} failed')
    return 0 if passed==len(names) else 1
