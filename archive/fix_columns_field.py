"""
Fix the columns field issue in the database.
The database has an old 'columns' field but the model uses 'custom_columns'.
"""

import os
import shutil
import sqlite3
from datetime import datetime

def backup_database(db_path):
    """Create a backup of the database."""
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return None
    
    backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(db_path, backup_path)
    print(f"Database backed up to: {backup_path}")
    return backup_path

def fix_columns_field(db_path):
    """Rename 'columns' field to 'custom_columns' and add is_deleted if missing."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("Checking database schema...")
        
        # Check current columns in project table
        cursor.execute("PRAGMA table_info(project)")
        columns = {col[1]: col for col in cursor.fetchall()}
        
        print(f"Current columns in project table: {list(columns.keys())}")
        
        # Check if we need to rename 'columns' to 'custom_columns'
        if 'columns' in columns and 'custom_columns' not in columns:
            print("📝 Renaming 'columns' to 'custom_columns'...")
            
            # SQLite doesn't support RENAME COLUMN directly in older versions
            # We need to recreate the table
            
            # 1. Create new table with correct schema
            cursor.execute("""
                CREATE TABLE project_new (
                    id INTEGER PRIMARY KEY,
                    name VARCHAR(160) NOT NULL,
                    user_id INTEGER NOT NULL,
                    created_at DATETIME,
                    custom_columns TEXT DEFAULT '[]',
                    FOREIGN KEY (user_id) REFERENCES user(id)
                )
            """)
            
            # 2. Copy data from old table
            cursor.execute("""
                INSERT INTO project_new (id, name, user_id, created_at, custom_columns)
                SELECT id, name, user_id, created_at, COALESCE(columns, '[]')
                FROM project
            """)
            
            # 3. Drop old table
            cursor.execute("DROP TABLE project")
            
            # 4. Rename new table
            cursor.execute("ALTER TABLE project_new RENAME TO project")
            
            print("'columns' renamed to 'custom_columns'")
        
        elif 'custom_columns' in columns:
            print("'custom_columns' already exists")
        
        else:
            print("Neither 'columns' nor 'custom_columns' found!")
            return False
        
        # Check requirement table for is_deleted
        cursor.execute("PRAGMA table_info(requirement)")
        req_columns = {col[1]: col for col in cursor.fetchall()}
        
        if 'is_deleted' not in req_columns:
            print("Adding 'is_deleted' to requirement table...")
            cursor.execute("""
                ALTER TABLE requirement ADD COLUMN is_deleted BOOLEAN DEFAULT 0
            """)
            print("'is_deleted' added")
        else:
            print("'is_deleted' already exists")
        
        conn.commit()
        print("Database schema fixed successfully!")
        return True
        
    except Exception as e:
        print(f"Error fixing schema: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False
    finally:
        conn.close()

def main():
    """Main function."""
    print("=" * 60)
    print("FIX COLUMNS FIELD IN DATABASE")
    print("=" * 60)
    
    # Determine database path
    instance_dir = os.path.join(os.path.dirname(__file__), 'instance')
    db_path = os.path.join(instance_dir, 'db.db')
    
    if not os.path.exists(db_path):
        print(f"Database not found at: {db_path}")
        return
    
    print(f"Database location: {db_path}")
    
    # Backup database
    backup_path = backup_database(db_path)
    if not backup_path:
        print("Failed to create backup. Aborting.")
        return
    
    # Fix schema
    success = fix_columns_field(db_path)
    
    if success:
        print("=" * 60)
        print("DATABASE FIXED SUCCESSFULLY!")
        print("=" * 60)
        print("\nYou can now:")
        print("1. Restart the application: python main.py")
        print("2. Create new projects without errors")
        print(f"\nBackup location: {backup_path}")
    else:
        print("\n" + "=" * 60)
        print("FAILED TO FIX DATABASE")
        print("=" * 60)
        print(f"\nRestore from backup:")
        print(f"copy \"{backup_path}\" \"{db_path}\"")

if __name__ == "__main__":
    main()
