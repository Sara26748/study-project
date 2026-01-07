from flask import Blueprint, current_app
from . import db
import re
import logging

logging.basicConfig(level=logging.INFO)

migration_bp = Blueprint('migration', __name__)

def normalize_key(title: str) -> str:
    """Creates a stable, lowercase key from a title string."""
    if not title:
        return ""
    s = title.strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s

@migration_bp.route('/migrate-now')
def migrate():
    logging.info("Migration route called.")
    try:
        # Check if the column already exists
        logging.info("Checking for 'key' column...")
        result = db.engine.execute("PRAGMA table_info(requirement)").fetchall()
        columns = [row[1] for row in result]
        if 'key' in columns:
            logging.info("'key' column already exists.")
            return "Migration already performed. The 'key' column already exists."

        # Add the 'key' column
        logging.info("Adding 'key' column...")
        db.engine.execute('ALTER TABLE requirement ADD COLUMN "key" VARCHAR(200)')
        logging.info("'key' column added.")
        
        # Populate the 'key' column
        logging.info("Populating 'key' column...")
        from .models import Requirement, RequirementVersion
        requirements = Requirement.query.all()
        logging.info(f"Found {len(requirements)} requirements to migrate.")
        for req in requirements:
            # Get the latest version to get the title
            latest_version = RequirementVersion.query.filter_by(requirement_id=req.id).order_by(RequirementVersion.version_index.desc()).first()
            if latest_version:
                req.key = normalize_key(latest_version.title)
                logging.info(f"  - Migrating req {req.id}, key: {req.key}")
        db.session.commit()
        logging.info("Population complete.")

        return "Migration successful! The 'key' column has been added and populated."
    except Exception as e:
        logging.error(f"An error occurred during migration: {e}")
        return f"An error occurred during migration: {e}"