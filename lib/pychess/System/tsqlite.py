""" This is a threadsafe wrapper sqlite.
    It is not classbased, so only one database can be open at a time """

try:
    # Python >= 2.5 has sqlite3 package in the standard library
    import sqlite3 as sqlite
except ImportError:
    try:
        # Python < 2.5
        import pysqlite2.dbapi2 as sqlite
    except ImportError:
        print """
PyChess was not able to import pysqlite2 which is a dependency to run the game.
PySqlite can be downloaded at http://initd.org/tracker/pysqlite
or on many packagesystems perhaps under the name python-sqlite2
"""
        import sys
        sys.exit()
    
import Queue, time, os
from threading import Thread

sqlqueue = Queue.Queue()

SQL_CMD, END_CMD = range(2)

class DbWrapper(Thread):
    def __init__(self, path):
        Thread.__init__(self)
        self.setDaemon(True)
        self.path = path
    
    def run(self):
        con = sqlite.connect(self.path)
        cur = con.cursor()
        while True:
            cmd, queries, resultqueue = sqlqueue.get()
            # print "Conn %d -> %s -> %s" % (self.nr, cmd, queries)
            if cmd == SQL_CMD:
                commitneeded = False
                res = []
                for sql in queries:
                    try:
                        cur.execute(sql)
                    except Exception, e:
                        print sql
                        raise e
                    if not sql.upper().startswith("SELECT"): 
                        commitneeded = True
                    res += cur.fetchall()
                if commitneeded: con.commit()
                resultqueue.put(res)
            else:
                # allow other threads to stop
                sqlqueue.put((cmd, queries, resultqueue))
                resultqueue.put(None)
                break

def connect (path):
    wrap = DbWrapper(path)
    wrap.start()

def close ():
    resultqueue = Queue.Queue()
    sqlqueue.put((END_CMD, [], resultqueue))
    resultqueue.get()

def execSQL (*queries):
    resultqueue = Queue.Queue()
    sqlqueue.put((SQL_CMD, queries, resultqueue))
    return resultqueue.get()

if __name__ == "__main__":
    dbname = "test.db"
    connect (dbname)
    execSQL ("drop table if exists people",
             "create table people (name_last, age integer)")
    # don't add connections before creating table
    connect (dbname)
    # insert one row
    execSQL ("insert into people (name_last, age) values ('Smith', 80)")
    # insert two rows in one transaction
    execSQL ("insert into people (name_last, age) values ('Jones', 55)", 
             "insert into people (name_last, age) values ('Gruns', 25)")
    for name, age in execSQL ("select * from people"):
        print "%s: %d" % (name, age)
    close()
    os.remove(dbname)
