import sqlite3
import pandas as pd
import os

def run_import():
    # File map based on what you provided
    files = {
        'msgs': 'message_chart (3).csv',
        'joins': 'members_chart (1).csv',
        'leaves': 'members_chart (2).csv',
        'total': 'members_chart.csv',
        'uniques': 'message_chart (2).csv'
    }

    # Load and clean dates
    dfs = {}
    for key, name in files.items():
        if os.path.exists(name):
            df = pd.read_csv(name)
            df['date'] = df['timestamp'].str[:10]
            dfs[key] = df
        else:
            print(f"Warning: {name} not found. Skipping.")

    # Merge everything on Date
    master = dfs['msgs'][['date', 'messages']]
    master = master.merge(dfs['joins'][['date', 'joins']], on='date', how='outer')
    master = master.merge(dfs['leaves'][['date', 'leaves']], on='date', how='outer')
    master = master.merge(dfs['total'][['date', 'members']], on='date', how='outer')
    # Use 'unique_count' temporarily
    master = master.merge(dfs['uniques'][['date', 'members']], on='date', how='outer', suffixes=('', '_unq'))
    
    master = master.fillna(0)

    conn = sqlite3.connect('analytics.db')
    c = conn.cursor()

    # Step 1: Ensure column exists (if not updated by main.py yet)
    try:
        c.execute("ALTER TABLE daily_stats ADD COLUMN total_mems INTEGER")
    except:
        pass # Column already exists

    for _, row in master.iterrows():
        # We store the unique count as a string number so our !stats command can handle it
        unique_val = str(int(row['members_unq']))
        
        c.execute("""INSERT OR IGNORE INTO daily_stats (date, msgs, joins, leaves, total_mems, unique_users) 
                     VALUES (?, ?, ?, ?, ?, ?)""", 
                  (row['date'], int(row['messages']), int(row['joins']), int(row['leaves']), int(row['members']), unique_val))
        
        # Update if exists
        c.execute("""UPDATE daily_stats SET msgs=?, joins=?, leaves=?, total_mems=?, unique_users=? 
                     WHERE date=?""", 
                  (int(row['messages']), int(row['joins']), int(row['leaves']), int(row['members']), unique_val, row['date']))

    conn.commit()
    conn.close()
    print(f"Import complete! Processed {len(master)} days of history.")

if __name__ == "__main__":
    run_import()