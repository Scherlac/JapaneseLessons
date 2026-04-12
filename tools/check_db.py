import sqlite3

con = sqlite3.connect("jlesson/rcm/rcm.db")
cur = con.cursor()
rows = cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
print("Tables:", [r[0] for r in rows])
try:
    ver = cur.execute("SELECT version_num FROM alembic_version").fetchall()
    print("alembic_version:", ver)
except Exception as e:
    print("No alembic_version table:", e)
con.close()
