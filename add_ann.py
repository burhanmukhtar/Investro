# update_announcement_table.py
import sqlite3
import os

# Get the current directory where the script is running
current_dir = os.path.dirname(os.path.abspath(__file__))

# Navigate to the database file
db_path = os.path.join(current_dir, 'instance', 'app.db')

print(f"Attempting to connect to database at: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if the database has the table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='announcement'")
    if not cursor.fetchone():
        print("The 'announcement' table doesn't exist! Please run your app migrations first.")
        conn.close()
        exit(1)
    
    # Get current columns in the table
    cursor.execute("PRAGMA table_info(announcement)")
    columns = [column[1] for column in cursor.fetchall()]
    
    # Add missing columns if they don't exist
    missing_columns = {
        'type': 'VARCHAR(50) DEFAULT "info"',
        'action_text': 'VARCHAR(100)',
        'action_url': 'VARCHAR(255)',
        'has_countdown': 'BOOLEAN DEFAULT 0',
        'expiry_date': 'DATETIME'
    }
    
    for column_name, column_type in missing_columns.items():
        if column_name not in columns:
            try:
                sql = f'ALTER TABLE announcement ADD COLUMN {column_name} {column_type}'
                cursor.execute(sql)
                print(f"Added column '{column_name}' to announcement table.")
            except sqlite3.OperationalError as e:
                print(f"Error adding column '{column_name}': {e}")
    
    # Commit the changes and close the connection
    conn.commit()
    print("Database update completed successfully.")
    
except Exception as e:
    print(f"Error: {e}")
    print("If the path is incorrect, please modify the script with the absolute path to your database.")
finally:
    if 'conn' in locals():
        conn.close()