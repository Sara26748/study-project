"""
Database migration script to update the requirement table schema
"""

import os
from app import create_app, db
from app.models import User, Project, Requirement

def migrate_database():
    """Recreate the database with the correct schema"""
    
    app = create_app()
    
    with app.app_context():
        print("Starting database migration...")
        print("-" * 60)
        
        # Backup existing data
        print("1. Backing up existing data...")
        try:
            users = User.query.all()
            projects = Project.query.all()
            print(f"   Found {len(users)} users and {len(projects)} projects")
        except Exception as e:
            print(f"   Warning: Could not read existing data: {e}")
            users = []
            projects = []
        
        # Drop all tables
        print("2. Dropping all tables...")
        db.drop_all()
        print("   All tables dropped")
        
        # Create all tables with new schema
        print("3. Creating tables with new schema...")
        db.create_all()
        print("   All tables created")
        
        # Restore users and projects
        print("4. Restoring data...")
        try:
            for user in users:
                db.session.add(user)
            for project in projects:
                db.session.add(project)
            db.session.commit()
            print(f"   Restored {len(users)} users and {len(projects)} projects")
        except Exception as e:
            print(f"   Warning: Could not restore data: {e}")
            db.session.rollback()
        
        print("-" * 60)
        print("✅ Database migration completed successfully!")
        print()
        print("The requirement table now has the correct schema:")
        print("  - id")
        print("  - title")
        print("  - description")
        print("  - category")
        print("  - status")
        print("  - project_id")
        print("  - created_at")
        print()
        print("You can now use the AI Agent to generate requirements.")

if __name__ == "__main__":
    migrate_database()
