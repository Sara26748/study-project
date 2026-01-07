"""
Database migration script to add new fields for additional features:
- Project sharing (project_user_association table)
- User tracking (created_by_id, last_modified_by_id)
- Blocking functionality (is_blocked, blocked_by_id, blocked_at)
"""

import sqlite3
import os

def migrate_database():
    db_path = os.path.join('instance', 'db.db')
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        print("Please ensure the database exists before running migration.")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("Starting database migration...")
        
        # 1. Create project_user_association table for project sharing
        print("Creating project_user_association table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS project_user_association (
                project_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                PRIMARY KEY (project_id, user_id),
                FOREIGN KEY (project_id) REFERENCES project(id),
                FOREIGN KEY (user_id) REFERENCES user(id)
            )
        ''')
        
        # 2. Add user tracking fields to requirement_version
        print("Adding user tracking fields to requirement_version...")
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(requirement_version)")
        existing_columns = [col[1] for col in cursor.fetchall()]
        
        if 'created_by_id' not in existing_columns:
            cursor.execute('''
                ALTER TABLE requirement_version 
                ADD COLUMN created_by_id INTEGER
            ''')
            print("  - Added created_by_id")
        else:
            print("  - created_by_id already exists")
        
        if 'last_modified_by_id' not in existing_columns:
            cursor.execute('''
                ALTER TABLE requirement_version 
                ADD COLUMN last_modified_by_id INTEGER
            ''')
            print("  - Added last_modified_by_id")
        else:
            print("  - last_modified_by_id already exists")
        
        # 3. Add blocking fields to requirement_version
        print("Adding blocking fields to requirement_version...")
        
        if 'is_blocked' not in existing_columns:
            cursor.execute('''
                ALTER TABLE requirement_version 
                ADD COLUMN is_blocked BOOLEAN DEFAULT 0
            ''')
            print("  - Added is_blocked")
        else:
            print("  - is_blocked already exists")
        
        if 'blocked_by_id' not in existing_columns:
            cursor.execute('''
                ALTER TABLE requirement_version 
                ADD COLUMN blocked_by_id INTEGER
            ''')
            print("  - Added blocked_by_id")
        else:
            print("  - blocked_by_id already exists")
        
        if 'blocked_at' not in existing_columns:
            cursor.execute('''
                ALTER TABLE requirement_version 
                ADD COLUMN blocked_at DATETIME
            ''')
            print("  - Added blocked_at")
        else:
            print("  - blocked_at already exists")
        
        # Commit changes
        conn.commit()
        print("\nMigration completed successfully!")
        print("\nNew features enabled:")
        print("  - Project sharing with other users")
        print("  - User tracking (created_by, modified_by)")
        print("  - Requirement blocking/locking")
        
        return True
        
    except Exception as e:
        print(f"\nMigration failed: {str(e)}")
        conn.rollback()
        return False
        
    finally:
        conn.close()

if __name__ == '__main__':
    print("=" * 60)
    print("Database Migration: Additional Features")
    print("=" * 60)
    print()
    
    success = migrate_database()
    
    if success:
        print("\n" + "=" * 60)
        print("Migration completed. You can now use the new features!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("Migration failed. Please check the error messages above.")
        print("=" * 60)
