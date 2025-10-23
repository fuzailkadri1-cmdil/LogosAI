"""Database migration script to add AI conversation fields"""
import sqlite3
import os

db_path = 'callcenter.db'

if os.path.exists(db_path):
    print(f"Backing up existing database to {db_path}.backup")
    import shutil
    shutil.copy(db_path, f'{db_path}.backup')

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check if table exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='call_logs'")
table_exists = cursor.fetchone()

if table_exists:
    # Check which columns exist
    cursor.execute('PRAGMA table_info(call_logs)')
    existing_columns = [col[1] for col in cursor.fetchall()]
    print(f"Existing columns: {existing_columns}")
    
    # Add missing columns
    new_columns = {
        'ai_conversation': 'TEXT',
        'ai_confidence': 'REAL',
        'conversation_turns': 'INTEGER DEFAULT 0',
        'escalation_reason': 'VARCHAR(100)'
    }
    
    for col_name, col_type in new_columns.items():
        if col_name not in existing_columns:
            try:
                cursor.execute(f'ALTER TABLE call_logs ADD COLUMN {col_name} {col_type}')
                print(f"✅ Added column: {col_name}")
            except sqlite3.OperationalError as e:
                print(f"❌ Error adding {col_name}: {e}")
else:
    print("❌ call_logs table doesn't exist - will be created on next app start")

conn.commit()
conn.close()
print("✅ Migration complete!")
