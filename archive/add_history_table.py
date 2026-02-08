"""
Migration script to add RequirementVersionHistory table for complete change tracking.
"""
import sqlite3
import os
from pathlib import Path
from datetime import datetime

def backup_database(db_path):
    """Create a backup of the database before migration."""
    backup_path = db_path.replace('.db', f'_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db')
    import shutil
    shutil.copy2(db_path, backup_path)
    print(f"Database backed up to: {backup_path}")
    return backup_path

def add_history_table(db_path):
    """Add RequirementVersionHistory table to track all changes."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("\nAdding RequirementVersionHistory table...")
        
        # Check if table already exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='requirement_version_history'
        """)
        
        if cursor.fetchone():
            print("Table 'requirement_version_history' already exists. Skipping.")
            return True
        
        # Create new table
        cursor.execute("""
            CREATE TABLE requirement_version_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version_id INTEGER NOT NULL,
                changed_by_id INTEGER NOT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                change_type VARCHAR(50) NOT NULL,
                changes TEXT DEFAULT '{}',
                FOREIGN KEY (version_id) REFERENCES requirement_version(id) ON DELETE CASCADE,
                FOREIGN KEY (changed_by_id) REFERENCES user(id)
            )
        """)
        
        print("Created requirement_version_history table")
        
        # Create index for faster queries
        cursor.execute("""
            CREATE INDEX idx_history_version_id ON requirement_version_history(version_id)
        """)
        cursor.execute("""
            CREATE INDEX idx_history_created_at ON requirement_version_history(created_at)
        """)
        
        print("Created indexes for requirement_version_history")
        
        conn.commit()
        print("\nMigration completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n Error: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False
    finally:
        conn.close()

def main():
    """Main function."""
    print("=" * 60)
    print("Migration: Add RequirementVersionHistory Table")
    print("=" * 60)
    
    # Find database path
    project_root = Path(__file__).parent
    instance_dir = project_root / "instance"
    db_path = instance_dir / "db.db"
    
    if not db_path.exists():
        print(f"Database not found at: {db_path}")
        print("   The database will be created automatically on first app start.")
        return
    
    print(f"📊 Database: {db_path}")
    
    # Backup database
    backup_database(str(db_path))
    
    # Run migration
    success = add_history_table(str(db_path))
    
    if success:
        print("\n" + "=" * 60)
        print("Migration completed successfully!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("Migration failed. Please check the error messages above.")
        print("=" * 60)

if __name__ == "__main__":
    main()

