"""
Database Schema Update Script for Versioning System

This script updates the existing database to support the new versioning system.
It adds the new tables and columns required for requirement versioning.

IMPORTANT: This will backup your database before making changes.
"""

import os
import shutil
import sqlite3
from datetime import datetime

def backup_database(db_path):
    """Create a backup of the database before migration."""
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return None
    
    backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(db_path, backup_path)
    print(f"✅ Database backed up to: {backup_path}")
    return backup_path

def update_schema(db_path):
    """Update the database schema to support versioning."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("\n🔄 Updating database schema...")
        
        # Check if requirement_version table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='requirement_version'
        """)
        
        if cursor.fetchone():
            print("⚠️  requirement_version table already exists. Checking columns...")
        else:
            print("📝 Creating requirement_version table...")
            cursor.execute("""
                CREATE TABLE requirement_version (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    requirement_id INTEGER NOT NULL,
                    version_index INTEGER NOT NULL,
                    version_label VARCHAR(4) NOT NULL,
                    title VARCHAR(160) NOT NULL,
                    description VARCHAR(2000) NOT NULL,
                    category VARCHAR(80),
                    status VARCHAR(30) NOT NULL DEFAULT 'Offen',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (requirement_id) REFERENCES requirement(id) ON DELETE CASCADE,
                    UNIQUE (requirement_id, version_index)
                )
            """)
            print("✅ requirement_version table created")
        
        # Check if requirement table has 'key' column
        cursor.execute("PRAGMA table_info(requirement)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'key' not in columns:
            print("📝 Adding 'key' column to requirement table...")
            cursor.execute("""
                ALTER TABLE requirement ADD COLUMN key VARCHAR(200)
            """)
            
            # Create index on key column
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_requirement_key ON requirement(key)
            """)
            print("✅ 'key' column added and indexed")
        else:
            print("✅ 'key' column already exists")
        
        conn.commit()
        print("\n✅ Schema update completed successfully!")
        return True
        
    except sqlite3.Error as e:
        print(f"\n❌ Error updating schema: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def main():
    """Main migration function."""
    print("=" * 60)
    print("DATABASE SCHEMA UPDATE FOR VERSIONING SYSTEM")
    print("=" * 60)
    
    # Determine database path
    instance_dir = os.path.join(os.path.dirname(__file__), 'instance')
    db_path = os.path.join(instance_dir, 'db.db')
    
    if not os.path.exists(db_path):
        print(f"\n❌ Database not found at: {db_path}")
        print("\nThis might be a new installation. The schema will be created")
        print("automatically when you run the application for the first time.")
        return
    
    print(f"\nDatabase location: {db_path}")
    
    # Backup database
    backup_path = backup_database(db_path)
    if not backup_path:
        print("\n❌ Failed to create backup. Aborting migration.")
        return
    
    # Update schema
    success = update_schema(db_path)
    
    if success:
        print("\n" + "=" * 60)
        print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Run the application: python main.py")
        print("2. If you have existing requirements, run: python migrate_versions.py")
        print("3. Test the versioning functionality")
        print(f"\nBackup location: {backup_path}")
        print("(Keep this backup until you've verified everything works)")
    else:
        print("\n" + "=" * 60)
        print("❌ MIGRATION FAILED")
        print("=" * 60)
        print(f"\nYour original database is safe at: {backup_path}")
        print("You can restore it by copying it back to: {db_path}")

if __name__ == "__main__":
    main()
