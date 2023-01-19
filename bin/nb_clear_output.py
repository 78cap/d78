#!/usr/bin/env python3
import json
import os
import stat
import sys


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    mode = os.fstat(0).st_mode
    if stat.S_ISFIFO(mode) or stat.S_ISREG(mode):
        nb = json.load(fp=sys.stdin)
    else:
        if len(argv) != 1:
            print(f'Usage: {__file__} filename.ipynb')
            return 1
        file_name = argv[0]
        with open(file_name, 'r') as f:
            nb = json.load(f)

    for cell in nb.get('cells') or []:
        cell.pop('outputs', None)
        cell.pop('execution_count', None)
    json.dump(nb, fp=sys.stdout, indent=1)
    return 0


if __name__ == '__main__':
    sys.exit(main())