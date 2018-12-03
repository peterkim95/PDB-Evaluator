import argparse
import logging

import lift
import table

def main():
    parser = argparse.ArgumentParser(description='perform pdb inference')
    parser.add_argument('-q', '--query', help='path to query file')
    parser.add_argument('-t', '--table', help='path to table file')
    parser.add_argument('-m', '--mcmc', help='use MCMC', action='store_true', default=False)
    args = parser.parse_args()

if __name__ == '__main__':
    main()
