
import re
import os
from flask import Flask
from app import create_app, db
from app.models import Project, Requirement as OldRequirement

# --- New Model Definitions ---
# Temporarily define the new models here for the migration script.
# This avoids conflicts if the main models.py is in a transitional state.

def version_label(n: int) -> str:
    """Generates a letter-based version label (1 -> A, 2 -> B, ...)."""
    if n <= 0:
        return ""
    return chr(ord('A') + (n - 1))

class Requirement(db.Model):
    __tablename__ = 'requirement'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    key = db.Column(db.String(200), index=True, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    versions = db.relationship(
        "RequirementVersion",
        backref="requirement",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="RequirementVersion.version_index.asc()"
    )

class RequirementVersion(db.Model):
    __tablename__ = 'requirement_version'
    id = db.Column(db.Integer, primary_key=True)
    requirement_id = db.Column(db.Integer, db.ForeignKey('requirement.id'), nullable=False)
    version_index = db.Column(db.Integer, nullable=False)
    version_label = db.Column(db.String(4), nullable=False)
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.String(2000), nullable=False)
    category = db.Column(db.String(80))
    status = db.Column(db.String(30), nullable=False, default="Offen")
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    __table_args__ = (
        db.UniqueConstraint('requirement_id', 'version_index', name='uq_req_version'),
    )

# --- Migration Logic ---

def normalize_key(title: str) -> str:
    """Creates a stable, lowercase key from a title string."""
    if not title:
        return ""
    s = title.strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s

def migrate_data(app: Flask):
    """
    Migrates data from the old single-table requirement structure to the new
    versioned structure.
    """
    with app.app_context():
        print("Starting data migration...")

        # This assumes the old table is still named 'requirement'
        # and the new ones are 'requirement' and 'requirement_version'.
        # We need to handle this carefully.
        
        # Step 1: Rename old requirement table to avoid conflicts
        db.engine.execute("ALTER TABLE requirement RENAME TO old_requirement")
        print("Renamed 'requirement' to 'old_requirement'.")

        # Step 2: Create the new tables
        db.create_all()
        print("Created new 'requirement' and 'requirement_version' tables.")

        # Step 3: Read from the old table and migrate data
        old_requirements_data = db.engine.execute("SELECT id, project_id, title, description, category, status, created_at FROM old_requirement").fetchall()

        if not old_requirements_data:
            print("No data found in 'old_requirement' table. Migration not needed.")
            # Clean up by dropping the empty old table
            db.engine.execute("DROP TABLE old_requirement")
            print("Dropped 'old_requirement' table.")
            db.session.commit()
            return

        print(f"Found {len(old_requirements_data)} records to migrate.")

        for old_data in old_requirements_data:
            title = old_data.title
            key = normalize_key(title)
            
            # Create the new logical Requirement
            new_req = Requirement(
                project_id=old_data.project_id,
                key=key,
                created_at=old_data.created_at
            )
            db.session.add(new_req)
            db.session.flush()  # Flush to get the ID for the version

            # Create the first RequirementVersion
            new_ver = RequirementVersion(
                requirement_id=new_req.id,
                version_index=1,
                version_label=version_label(1),
                title=title,
                description=old_data.description,
                category=old_data.category,
                status=old_data.status,
                created_at=old_data.created_at
            )
            db.session.add(new_ver)
        
        # Step 4: Commit all changes
        db.session.commit()
        print("Successfully migrated data.")

        # Step 5: Drop the old table
        db.engine.execute("DROP TABLE old_requirement")
        print("Dropped 'old_requirement' table.")
        db.session.commit()

        print("Migration complete!")


if __name__ == "__main__":
    # This script must be run in the context of your Flask app
    # to have access to the database configuration.
    app = create_app()
    if not app:
        raise RuntimeError("Could not create Flask app. Check your app factory configuration.")
    
    # IMPORTANT: Make sure your models.py reflects the NEW structure
    # before running this script.
    migrate_data(app)
