import sqlite3
conn = sqlite3.connect('nutriguard.db')
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in c.fetchall()]
print('Tables:', tables)
for t in ['foods','medications','conditions','allergies','drug_food_interactions','condition_nutrition_rules','users']:
    if t in tables:
        c.execute(f'SELECT COUNT(*) FROM {t}')
        print(f'{t}: {c.fetchone()[0]} rows')
# Sample data
c.execute("SELECT name FROM foods LIMIT 10")
print('Foods:', [r[0] for r in c.fetchall()])
c.execute("SELECT generic_name FROM medications LIMIT 10")
print('Meds:', [r[0] for r in c.fetchall()])
c.execute("SELECT name FROM conditions LIMIT 10")
print('Conditions:', [r[0] for r in c.fetchall()])
conn.close()
