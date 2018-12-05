import os
import logging
import sqlite3
import pandas as pd

logging.basicConfig(level=logging.INFO)
_LOGGER = logging.getLogger(__name__)

class SQLDatabase:
    def __init__(self, db_name=":memory:", table_files=[], is_nell=False):
        self.db_conn = sqlite3.connect(db_name)
        if is_nell:
            self._create_tables_from_nell_csv(table_files[0])
        else:
            for fname in table_files:
                self._create_table_from_csv(fname)

    def _create_table_from_df(self, table_name, dataframe, type='INT'):
        col_names = ['c{}'.format(i) for i in range(len(dataframe.columns)-1)] + ['Pr']
        col_names_str = ','.join(map(lambda c: c + ' {}'.format(type), col_names[:-1])) + ',Pr FLOAT'

        # create table
        self.db_conn.execute('DROP TABLE IF EXISTS {}'.format(table_name))
        self.db_conn.execute('CREATE TABLE {}({});'.format(table_name, col_names_str))

        # extension - create index for faster lookup
        self.db_conn.execute('CREATE INDEX {}_index ON {}({})'.format(table_name, table_name, ', '.join(col_names[:-1])))

        dataframe.columns = col_names
        dataframe.to_sql(table_name, self.db_conn, if_exists='append', index=False)

        self.db_conn.commit()

    def _create_tables_from_nell_csv(self, fname):
        with open(fname) as csv_file:
            df = pd.read_csv(csv_file, header=0, sep='\t')
            # prune irrelevant columns
            df = df.ix[:, ['Entity', 'Relation', 'Value', 'Probability']]

            for table_name, indices in df.groupby('Relation').groups.items():
                tmp_df = df.ix[indices, ['Entity', 'Value', 'Probability']]
                self._create_table_from_df(table_name.split(':')[-1], tmp_df, type='TEXT')

    def _create_table_from_csv(self, fname, delimiter=','):
        with open(fname) as csv_file:
            #read the first column to get table name
            table_name = csv_file.readline()[:-1]
            df = pd.read_csv(csv_file, header=None, sep=delimiter)
            self._create_table_from_df(table_name, df)

    def _execute_query(self, query):
        cur = self.db_conn.cursor()
        cur.execute(query)
        return cur.fetchall()

    def lookup(self, table, var):
        where_clause = ' WHERE'
        for i, v in enumerate(tuple(var)):
            where_clause += ' c{} = {} AND'.format(i, v)

        q = 'SELECT Pr FROM {}'.format(table) + where_clause[:-3]
        rows = self._execute_query(q)

        if not rows: # closed-world assumption
            return 0
        return rows[0][0]

    def ground(self, table, varindex):
        q = 'SELECT * FROM {}'.format(table)
        g = [str(row[varindex]) for row in self._execute_query(q)]
        return set(g)

def main():
    table_files_dir = 'data/table_files'
    tfs = [os.path.join(table_files_dir, file) for file in os.listdir(table_files_dir)]

    # basic tests
    # db = SQLDatabase(table_files=tfs)
    # print(db.lookup('P', ('0',)))
    # print(db.lookup('R', ('0','0')))

    # nell test
    db = SQLDatabase(table_files=['nell_test.csv'], is_nell=True)

if __name__ == '__main__':
    main()
