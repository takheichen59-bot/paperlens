"""Independent audit self-check; excluded from module acceptance counts."""
import argparse
from pathlib import Path
from audit_leakage import DEFAULT_TRUTH, self_check

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--cache',type=Path,required=True)
    parser.add_argument('--ground-truth',type=Path,default=DEFAULT_TRUTH)
    args=parser.parse_args()
    raise SystemExit(self_check(args.output,args.cache,args.ground_truth))
