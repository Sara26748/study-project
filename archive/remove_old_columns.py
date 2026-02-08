"""
Remove old 'columns' field and other obsolete fields from project table.
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
    print(f"✅ Database backed up to: {backup_path}")
    return backup_path

def remove_old_columns(db_path):
    """Remove old columns from project table."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("\n🔄 Removing old columns from project table...")
        
        # Check current columns
        cursor.execute("PRAGMA table_info(project)")
        columns = {col[1]: col for col in cursor.fetchall()}
        
        print(f"Current columns: {list(columns.keys())}")
        
        # Create new table with only the columns we need
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
        print("✅ Created new project table")
        
        # Copy data from old table (only the columns we want)
        cursor.execute("""
            INSERT INTO project_new (id, name, user_id, created_at, custom_columns)
            SELECT id, name, user_id, created_at, COALESCE(custom_columns, '[]')
            FROM project
        """)
        print("✅ Copied data to new table")
        
        # Drop old table
        cursor.execute("DROP TABLE project")
        print("✅ Dropped old table")
        
        # Rename new table
        cursor.execute("ALTER TABLE project_new RENAME TO project")
        print("✅ Renamed new table to 'project'")
        
        conn.commit()
        print("\n✅ Old columns removed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False
    finally:
        conn.close()

def main():
    """Main function."""
    print("=" * 60)
    print("REMOVE OLD COLUMNS FROM PROJECT TABLE")
    print("=" * 60)
    
    # Determine database path
    instance_dir = os.path.join(os.path.dirname(__file__), 'instance')
    db_path = os.path.join(instance_dir, 'db.db')
    
    if not os.path.exists(db_path):
        print(f"\n❌ Database not found at: {db_path}")
        return
    
    print(f"\nDatabase location: {db_path}")
    
    # Backup database
    backup_path = backup_database(db_path)
    if not backup_path:
        print("\n❌ Failed to create backup. Aborting.")
        return
    
    # Remove old columns
    success = remove_old_columns(db_path)
    
    if success:
        print("\n" + "=" * 60)
        print("✅ DATABASE CLEANED SUCCESSFULLY!")
        print("=" * 60)
        print("\nRemoved columns:")
        print("- columns (old)")
        print("- created_requirements (obsolete)")
        print("- intermediate_requirements (obsolete)")
        print("- saved_requirements (obsolete)")
        print("- deleted_requirements (obsolete)")
        print("\nKept columns:")
        print("- id")
        print("- name")
        print("- user_id")
        print("- created_at")
        print("- custom_columns")
        print(f"\nBackup location: {backup_path}")
        print("\n🚀 Restart the application: python main.py")
    else:
        print("\n" + "=" * 60)
        print("❌ FAILED TO CLEAN DATABASE")
        print("=" * 60)
        print(f"\nRestore from backup:")
        print(f"copy \"{backup_path}\" \"{db_path}\"")

if __name__ == "__main__":
    main()
