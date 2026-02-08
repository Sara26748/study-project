"""
Add new columns to database for dynamic columns and custom data features.
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

def add_columns(db_path):
    """Add new columns to existing tables."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("\nAdding new columns...")
        
        # Check if project table has custom_columns
        cursor.execute("PRAGMA table_info(project)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'custom_columns' not in columns:
            print("Adding 'custom_columns' to project table...")
            cursor.execute("""
                ALTER TABLE project ADD COLUMN custom_columns TEXT DEFAULT '[]'
            """)
            print("'custom_columns' column added")
        else:
            print("'custom_columns' column already exists")
        
        # Check if requirement_version table has custom_data
        cursor.execute("PRAGMA table_info(requirement_version)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'custom_data' not in columns:
            print("Adding 'custom_data' to requirement_version table...")
            cursor.execute("""
                ALTER TABLE requirement_version ADD COLUMN custom_data TEXT DEFAULT '{}'
            """)
            print("'custom_data' column added")
        else:
            print("'custom_data' column already exists")
        
        conn.commit()
        print("\nColumns added successfully!")
        return True
        
    except Exception as e:
        print(f"\nError adding columns: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False
    finally:
        conn.close()

def main():
    """Main function."""
    print("=" * 60)
    print("ADD NEW COLUMNS FOR DYNAMIC FEATURES")
    print("=" * 60)
    
    # Determine database path
    instance_dir = os.path.join(os.path.dirname(__file__), 'instance')
    db_path = os.path.join(instance_dir, 'db.db')
    
    if not os.path.exists(db_path):
        print(f"\nDatabase not found at: {db_path}")
        return
    
    print(f"\nDatabase location: {db_path}")
    
    # Backup database
    backup_path = backup_database(db_path)
    if not backup_path:
        print("\nFailed to create backup. Aborting.")
        return
    
    # Add columns
    success = add_columns(db_path)
    
    if success:
        print("\n" + "=" * 60)
        print("COLUMNS ADDED SUCCESSFULLY!")
        print("=" * 60)
        print("\nYou can now:")
        print("1. Start the application: python main.py")
        print("2. Add custom columns to your projects")
        print("3. Use the new features")
        print(f"\nBackup location: {backup_path}")
    else:
        print("\n" + "=" * 60)
        print("FAILED TO ADD COLUMNS")
        print("=" * 60)
        print(f"\nRestore from backup:")
        print(f"copy \"{backup_path}\" \"{db_path}\"")

if __name__ == "__main__":
    main()
