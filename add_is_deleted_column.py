"""
Add is_deleted column to Requirement table for soft delete functionality.
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

def add_column(db_path):
    """Add is_deleted column to Requirement table."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("\nAdding is_deleted column to Requirement table...")
        
        # Check if requirement table has is_deleted column
        cursor.execute("PRAGMA table_info(requirement)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'is_deleted' not in columns:
            print("Adding 'is_deleted' column to requirement table...")
            cursor.execute("""
                ALTER TABLE requirement ADD COLUMN is_deleted BOOLEAN DEFAULT 0
            """)
            print("'is_deleted' column added")
        else:
            print("'is_deleted' column already exists")
        
        conn.commit()
        print("\nColumn added successfully!")
        return True
        
    except Exception as e:
        print(f"\nError adding column: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False
    finally:
        conn.close()

def main():
    """Main function."""
    print("=" * 60)
    print("ADD IS_DELETED COLUMN FOR SOFT DELETE")
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
    
    # Add column
    success = add_column(db_path)
    
    if success:
        print("\n" + "=" * 60)
        print("✅ COLUMN ADDED SUCCESSFULLY!")
        print("=" * 60)
        print("\nYou can now:")
        print("1. Start the application: python main.py")
        print("2. Use the soft delete functionality")
        print(f"\nBackup location: {backup_path}")
    else:
        print("\n" + "=" * 60)
        print("❌ FAILED TO ADD COLUMN")
        print("=" * 60)
        print(f"\nRestore from backup:")
        print(f"copy \"{backup_path}\" \"{db_path}\"")

if __name__ == "__main__":
    main()
