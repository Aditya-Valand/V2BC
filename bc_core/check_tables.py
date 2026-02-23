import sqlite3

conn = sqlite3.connect('bc_dev.db')
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = c.fetchall()
for table in tables:
    print(f'Table: {table[0]}')
conn.close()
