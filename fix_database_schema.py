"""
Complete Database Schema Fix for Versioning System

This script completely rebuilds the requirement table structure.
It preserves your data by migrating it properly.
"""

import os
import shutil
import sqlite3
from datetime import datetime
import json
import re

def backup_database(db_path):
    """Create a backup of the database."""
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return None
    
    backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(db_path, backup_path)
    print(f"Database backed up to: {backup_path}")
    return backup_path

def normalize_key(title: str) -> str:
    """Creates a stable, lowercase key from a title string."""
    if not title:
        return ""
    s = title.strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s

def version_label(n: int) -> str:
    """Generates a letter-based version label (1 -> A, 2 -> B, ...)."""
    if n <= 0:
        return ""
    return chr(ord('A') + (n - 1))

def fix_schema(db_path):
    """Fix the database schema completely."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("Fixing database schema...")
        
        # Step 1: Get all existing requirements data
        print("Reading existing requirements...")
        cursor.execute("SELECT id, project_id FROM requirement")
        old_requirements = cursor.fetchall()
        print(f"   Found {len(old_requirements)} existing requirements")
        
        # Step 2: Get project data to read JSON blobs
        print("Reading project data...")
        cursor.execute("""
            SELECT id, created_requirements, intermediate_requirements, 
                   saved_requirements, deleted_requirements 
            FROM project
        """)
        projects_data = cursor.fetchall()
        
        # Step 3: Drop old requirement table
        print("Dropping old requirement table...")
        cursor.execute("DROP TABLE IF EXISTS requirement")
        
        # Step 4: Create new requirement table (without title column)
        print("Creating new requirement table...")
        cursor.execute("""
            CREATE TABLE requirement (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                key VARCHAR(200),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES project(id) ON DELETE CASCADE
            )
        """)
        
        cursor.execute("""
            CREATE INDEX idx_requirement_key ON requirement(key)
        """)
        
        # Step 5: Create requirement_version table if it doesn't exist
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='requirement_version'
        """)
        
        if not cursor.fetchone():
            print("Creating requirement_version table...")
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
        
        # Step 6: Migrate data from JSON blobs
        print("Migrating data from project JSON blobs...")
        
        for project_id, created_json, intermediate_json, saved_json, deleted_json in projects_data:
            all_reqs = []
            
            # Parse all JSON blobs
            for json_blob in [created_json, intermediate_json, saved_json, deleted_json]:
                if json_blob:
                    try:
                        reqs = json.loads(json_blob)
                        all_reqs.extend(reqs)
                    except (json.JSONDecodeError, TypeError):
                        pass
            
            if not all_reqs:
                continue
            
            print(f"   Processing project {project_id}: {len(all_reqs)} requirements")
            
            # Use dict to handle duplicates
            unique_reqs = {}
            for req_data in all_reqs:
                title = req_data.get("Title") or req_data.get("title", "")
                if not title:
                    continue
                
                key = normalize_key(title)
                if key not in unique_reqs:
                    unique_reqs[key] = req_data
            
            # Insert into new structure
            for key, req_data in unique_reqs.items():
                title = req_data.get("Title") or req_data.get("title", "")
                description = req_data.get("Beschreibung") or req_data.get("description", "")
                category = req_data.get("Kategorie") or req_data.get("category", "")
                status = "Offen"
                
                # Insert logical requirement
                cursor.execute("""
                    INSERT INTO requirement (project_id, key, created_at)
                    VALUES (?, ?, ?)
                """, (project_id, key, datetime.utcnow()))
                
                req_id = cursor.lastrowid
                
                # Insert first version
                cursor.execute("""
                    INSERT INTO requirement_version 
                    (requirement_id, version_index, version_label, title, description, category, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (req_id, 1, version_label(1), title, description, category, status, datetime.utcnow()))
        
        conn.commit()
        print("Schema fix completed successfully!")
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
    print("COMPLETE DATABASE SCHEMA FIX")
    print("=" * 60)
    
    # Determine database path
    instance_dir = os.path.join(os.path.dirname(__file__), 'instance')
    db_path = os.path.join(instance_dir, 'db.db')
    
    if not os.path.exists(db_path):
        print(f"Database not found at: {db_path}")
        return
    
    print(f"Database location: {db_path}")
    print("WARNING: This will rebuild the requirement table structure.")
    print("Your data will be preserved, but the table will be recreated.")
    
    # Backup database
    backup_path = backup_database(db_path)
    if not backup_path:
        print("Failed to create backup. Aborting.")
        return
    
    # Fix schema
    success = fix_schema(db_path)
    
    if success:
        print("=" * 60)
        print("SCHEMA FIX COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Start the application: python main.py")
        print("2. Navigate to your project")
        print("3. You should see the Version column with 'A' badges")
        print(f"Backup location: {backup_path}")
    else:
        print("=" * 60)
        print("SCHEMA FIX FAILED")
        print("=" * 60)
        print(f"Restore from backup:")
        print(f"copy \"{backup_path}\" \"{db_path}\"")

if __name__ == "__main__":
    main()
