import sqlite3

conn = sqlite3.connect('bc_dev.db')
c = conn.cursor()
c.execute('DROP TABLE IF EXISTS user_organization_permission')
c.execute("DELETE FROM alembic_version WHERE version_num = '0b53f46e508e'")
conn.commit()
conn.close()
print('Cleaned up database state')
