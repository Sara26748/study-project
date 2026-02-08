"""
Migration script to add RequirementComment and Notification tables.
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

def add_tables(db_path):
    """Add RequirementComment and Notification tables."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("\nAdding RequirementComment and Notification tables...")
        
        # Check if tables already exist
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='requirement_comment'
        """)
        
        if cursor.fetchone():
            print("Table 'requirement_comment' already exists. Skipping.")
        else:
            # Create RequirementComment table
            cursor.execute("""
                CREATE TABLE requirement_comment (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version_id INTEGER NOT NULL,
                    author_id INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    parent_comment_id INTEGER,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    is_deleted BOOLEAN NOT NULL DEFAULT 0,
                    FOREIGN KEY (version_id) REFERENCES requirement_version(id) ON DELETE CASCADE,
                    FOREIGN KEY (author_id) REFERENCES user(id),
                    FOREIGN KEY (parent_comment_id) REFERENCES requirement_comment(id) ON DELETE CASCADE
                )
            """)
            print("Created requirement_comment table")
            
            # Create indexes for comments
            cursor.execute("""
                CREATE INDEX idx_comment_version_id ON requirement_comment(version_id)
            """)
            cursor.execute("""
                CREATE INDEX idx_comment_parent_id ON requirement_comment(parent_comment_id)
            """)
            cursor.execute("""
                CREATE INDEX idx_comment_created_at ON requirement_comment(created_at)
            """)
            print("Created indexes for requirement_comment")
        
        # Check if Notification table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='notification'
        """)
        
        if cursor.fetchone():
            print("Table 'notification' already exists. Skipping.")
        else:
            # Create Notification table
            cursor.execute("""
                CREATE TABLE notification (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    notification_type VARCHAR(50) NOT NULL,
                    title VARCHAR(200) NOT NULL,
                    message TEXT,
                    related_type VARCHAR(50),
                    related_id INTEGER,
                    metadata TEXT DEFAULT '{}',
                    is_read BOOLEAN NOT NULL DEFAULT 0,
                    read_at DATETIME,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
                )
            """)
            print("Created notification table")
            
            # Create indexes for notifications
            cursor.execute("""
                CREATE INDEX idx_notification_user_id ON notification(user_id)
            """)
            cursor.execute("""
                CREATE INDEX idx_notification_is_read ON notification(is_read)
            """)
            cursor.execute("""
                CREATE INDEX idx_notification_created_at ON notification(created_at)
            """)
            print("Created indexes for notification")
        
        conn.commit()
        print("\nMigration completed successfully!")
        return True
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False
    finally:
        conn.close()

def main():
    """Main function."""
    print("=" * 60)
    print("Migration: Add RequirementComment and Notification Tables")
    print("=" * 60)
    
    # Find database path
    project_root = Path(__file__).parent
    instance_dir = project_root / "instance"
    db_path = instance_dir / "db.db"
    
    if not db_path.exists():
        print(f"Database not found at: {db_path}")
        print("   The database will be created automatically on first app start.")
        return
    
    print(f"Database: {db_path}")
    
    # Backup database
    backup_database(str(db_path))
    
    # Run migration
    success = add_tables(str(db_path))
    
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

