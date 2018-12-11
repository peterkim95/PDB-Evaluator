import argparse
from lift import Lifter

def main():
    parser = argparse.ArgumentParser(description='perform pdb inference')
    parser.add_argument('-q', '--query', help='path to query file')
    parser.add_argument('-t', '--table', action='append', nargs='*', help='path to table file')
    parser.add_argument('-s', '--speedup', help='use sql speedup', action='store_true', default=False)
    args = parser.parse_args()
    args.table = [item for sublist in args.table for item in sublist] # flatten 2d list

    l = Lifter(args.table, args.speedup)
    # perform inference for all queries
    with open(args.query) as f:
        for query in f:
            q = query.rstrip('\n')
            print('*** Pr({}) = {} ***'.format(q, l.lift(q)))

if __name__ == '__main__':
    main()
