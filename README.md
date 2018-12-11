# PDB-Evaluator
A Python-based inference system for Probabilistic Databases

## Setup
1. Make sure you have virtualenv and python3 on your system.
2. Run `make dev` to set up a virtualenv and installing dependencies.

## Usage

### Basic Usage

To run inference on given queries with respect to given table csv files:

`python pdb_main.py -q data/query_files/query.txt -t data/table_files/T1.txt -t data/table_files/T2.txt -t data/table_files/T3.txt`

### Enable PDB
