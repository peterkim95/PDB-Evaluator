import logging
import sqlite3
import pandas as pd

logging.basicConfig(level=logging.INFO)
_LOGGER = logging.getLogger(__name__)

class SQLDatabase:
    def __init__(self, db_name=":memory:", table_files=[]):
        self.db_conn = sqlite3.connect(db_name)


        for fname in table_files:
            self._create_table_from_csv(fname)
            
    def _create_table_from_csv(self, fname):
        with open(fname) as csv_file:
            #read the first column to get table name
            table_name = csv_file.readline()[:-1]
            df = pd.read_csv(csv_file, header=None)
            
            col_names = ['c{}'.format(i) for i in range(len(df.columns)-1)] + ['P']
            col_names_str = ','.join(map(lambda c: c + " INT", col_names[:-1])) + ",P FLOAT" 

            #create table
            self.db_conn.execute("DROP TABLE IF EXISTS {}".format(table_name))
            self.db_conn.execute("CREATE TABLE {}({});".format(table_name, col_names_str))
             
            df.columns = col_names
            df.to_sql(table_name, self.db_conn, if_exists='append', index=False)
            
            self.db_conn.commit()
