#!/usr/bin/env python3

import csv


def main(args):
    with open(parser.source, newline='') as source_file:
        reader = csv.reader(source_file)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', '-s', help='Source CSV file')
    main(parser.parse_args())
