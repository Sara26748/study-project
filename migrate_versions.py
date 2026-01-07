import json
import re
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app, db
from app.models import Project, Requirement, RequirementVersion, version_label

def normalize_key(title: str) -> str:
    """Creates a stable, lowercase key from a title string."""
    if not title:
        return ""
    s = title.strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s

def run_migration():
    """
    Migrates data from old JSON blob columns in the Project table to the new
    versioned Requirement and RequirementVersion tables.

    This script should be run ONCE after updating the models.
    It is highly recommended to BACK UP your database before running this.

    This script does NOT alter the database schema (e.g., drop old columns).
    Use a migration tool like Flask-Migrate (Alembic) for schema changes.
    """
    app = create_app()
    with app.app_context():
        print("Starting data migration...")
        projects = Project.query.all()
        
        for project in projects:
            print(f"Processing project: '{project.name}' (ID: {project.id})")
            
            # Use direct connection to get old data, as model attributes are removed
            connection = db.engine.connect()
            result = connection.execute(
                db.text(
                    "SELECT created_requirements, intermediate_requirements, saved_requirements, deleted_requirements FROM project WHERE id = :id"
                ),
                {"id": project.id}
            ).first()
            
            if not result:
                print(f"  -> No old data found for project {project.id}. Skipping.")
                connection.close()
                continue

            old_req_blobs = {
                "created": result[0],
                "intermediate": result[1],
                "saved": result[2],
                "deleted": result[3]
            }

            all_old_reqs = []
            for status, blob in old_req_blobs.items():
                try:
                    reqs = json.loads(blob)
                    # Add status to each req, might be useful
                    for r in reqs:
                        r['migration_status'] = status
                    all_old_reqs.extend(reqs)
                except (json.JSONDecodeError, TypeError):
                    print(f"  -> Warning: Could not parse JSON for '{status}' in project {project.id}. Skipping blob.")
            
            if not all_old_reqs:
                print(f"  -> No requirements found in old JSON blobs for project {project.id}.")
                connection.close()
                continue

            # Use a dictionary to handle potential duplicates by title across lists
            unique_reqs_by_key = {}
            for req_data in all_old_reqs:
                # The old structure had data in the root dict
                title = req_data.get("Title") or req_data.get("title") # Check for both cases
                if not title:
                    print(f"  -> Skipping requirement with no title: {req_data}")
                    continue
                
                key = normalize_key(title)
                if key in unique_reqs_by_key:
                    # If we see the same requirement again (e.g., in 'saved' after 'created'),
                    # we just ignore it for this simple migration. We only create one "Version A".
                    continue
                
                unique_reqs_by_key[key] = req_data

            print(f"  -> Found {len(unique_reqs_by_key)} unique requirements to migrate.")

            for key, req_data in unique_reqs_by_key.items():
                # Check if this requirement has already been migrated
                existing_req = Requirement.query.filter_by(project_id=project.id, key=key).first()
                if existing_req:
                    print(f"    -> Requirement with key '{key}' already exists. Skipping.")
                    continue

                # 1. Create the logical Requirement
                new_logical_req = Requirement(project_id=project.id, key=key)
                db.session.add(new_logical_req)
                # Flush to get the ID for the version
                db.session.flush()

                # 2. Create the first version (Version A)
                title = req_data.get("Title") or req_data.get("title")
                description = req_data.get("Beschreibung") or req_data.get("description", "")
                category = req_data.get("Kategorie") or req_data.get("category", "")
                
                # Determine status based on which list it was in
                mig_status = req_data.get('migration_status')
                if mig_status == 'saved':
                    status = "Gespeichert"
                elif mig_status == 'intermediate':
                    status = "Zwischengespeichert"
                else: # created, deleted, or default
                    status = "Offen"


                version = RequirementVersion(
                    requirement_id=new_logical_req.id,
                    version_index=1,
                    version_label=version_label(1),
                    title=title,
                    description=description,
                    category=category,
                    status=status
                )
                db.session.add(version)
                print(f"    -> Migrated '{title}' as Version A.")

            connection.close()

        print("Committing changes to the database...")
        db.session.commit()
        print("Migration complete!")

if __name__ == "__main__":
    run_migration()
