from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func, and_
from datetime import datetime
import json
from . import db
from .models import Project, Requirement, RequirementVersion, RequirementComment, Notification, User
from .services.ai_client import generate_requirements

bp = Blueprint('main', __name__)


def _int_to_roman(num: int) -> str:
    """Convert integer to Roman numerals (supports positive numbers)."""
    if num <= 0:
        return ""
    mapping = [
        (1000, "M"),
        (900, "CM"),
        (500, "D"),
        (400, "CD"),
        (100, "C"),
        (90, "XC"),
        (50, "L"),
        (40, "XL"),
        (10, "X"),
        (9, "IX"),
        (5, "V"),
        (4, "IV"),
        (1, "I"),
    ]
    result = ""
    for value, numeral in mapping:
        while num >= value:
            result += numeral
            num -= value
    return result


def _roman_to_int(value: str) -> int:
    """Convert Roman numerals to integer; returns 0 if invalid/empty."""
    if not value:
        return 0
    mapping = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total = 0
    prev = 0
    for ch in reversed(value.upper()):
        current = mapping.get(ch, 0)
        if current < prev:
            total -= current
        else:
            total += current
            prev = current
    return total

# Route: Manuelle Anforderung erstellen
@bp.route("/project/<int:project_id>/manual_requirement", methods=["POST"])
@login_required
def create_manual_requirement(project_id):
    project = Project.query.get_or_404(project_id)
    check_project_access(project)

    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    category = request.form.get("category", "").strip()
    status = request.form.get("status", "Entwurf").strip()
    is_quantifiable = request.form.get("is_quantifiable") == "on"
    funktional = request.form.get("funktional") == "on"

    if not title or not description:
        flash("Name und Beschreibung sind erforderlich.", "danger")
        return redirect(url_for('main.manage_project', project_id=project_id))

    # Key für Duplikatserkennung
    from .agent import normalize_key
    key = normalize_key(title)
    req = Requirement.query.filter_by(project_id=project_id, key=key).first()
    if not req:
        req = Requirement(project_id=project_id, key=key, funktional=funktional)
        db.session.add(req)
        db.session.flush()
        version_index = 1
        version_label = 'A'
    else:
        # Update funktional, falls geändert
        if req.funktional != funktional:
            req.funktional = funktional
        last_version = req.versions[-1] if req.versions else None
        version_index = last_version.version_index + 1 if last_version else 1
        version_label = chr(ord('A') + (version_index - 1))

    new_version = RequirementVersion(
        requirement_id=req.id,
        version_index=version_index,
        version_label=version_label,
        title=title,
        description=description,
        category=category,
        status=status,
        revision="Entwurf",
        created_by_id=current_user.id
    )
    # Custom Data
    custom_data = {}
    if is_quantifiable:
        custom_data['is_quantifiable'] = 'true'
    else:
        custom_data['is_quantifiable'] = 'false'
    # Dynamische Spalten
    for col in project.get_custom_columns():
        val = request.form.get(f'custom_{col}', '').strip()
        if val:
            custom_data[col] = val
    if custom_data:
        new_version.set_custom_data(custom_data)
    db.session.add(new_version)
    db.session.flush()
    # History
    from .models import RequirementVersionHistory
    import json
    history_entry = RequirementVersionHistory(
        version_id=new_version.id,
        changed_by_id=current_user.id,
        change_type='created',
        changes=json.dumps({'action': 'Manuell erstellt', 'version': version_label})
    )
    db.session.add(history_entry)
    db.session.commit()
    # Notification
    try:
        notify_requirement_created(new_version, current_user)
    except Exception:
        pass
    flash(f"Anforderung '{title}' wurde erfolgreich erstellt.", "success")
    return redirect(url_for('main.manage_project', project_id=project_id))

def check_project_access(project):
    """Check if current user has access to the project (owner or shared)."""
    if project.user_id != current_user.id and current_user not in project.shared_with:
        abort(403)

def check_requirement_access(requirement):
    """Check if current user has access to the requirement's project (owner or shared)."""
    check_project_access(requirement.project)

def check_version_access(version):
    """Check if current user has access to the version's requirement project (owner or shared)."""
    check_project_access(version.requirement.project)

@bp.route("/")
@login_required
def home():
    # Get projects owned by the user
    owned_projects = Project.query.filter_by(user_id=current_user.id).all()
    
    # Get projects shared with the user
    shared_projects = current_user.shared_projects.all()
    
    # Combine both lists (owned first, then shared)
    projects = owned_projects + shared_projects
    
    return render_template("start.html", projects=projects)


@bp.route("/project/<int:project_id>/mention_suggestions")
@login_required
def mention_suggestions(project_id):
    project = Project.query.get_or_404(project_id)
    check_project_access(project)

    q = (request.args.get("q", "") or "").strip().lower()

    # Kandidaten: Owner + shared_with + current_user
    candidates = []

    owner = User.query.get(project.user_id)
    if owner:
        candidates.append(owner)

    for u in project.shared_with:
        candidates.append(u)

    candidates.append(current_user)

    # Duplikate entfernen
    uniq = {}
    for u in candidates:
        uniq[u.id] = u

    results = []
    for u in uniq.values():
        email = u.email or ""
        username = (email.split("@")[0] if email else "").strip()

        # Filter: query passt in username oder email
        if not q or q in username.lower() or q in email.lower():
            results.append({
                "id": u.id,
                "username": username,
                "email": email
            })

    results = sorted(results, key=lambda x: (x["username"] or x["email"]))[:8]
    return jsonify({"users": results})

@bp.route("/create", methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        project_name = request.form.get('project_name')
        if project_name:
            # The concept of dynamic columns is removed in the new model.
            new_project = Project(name=project_name, user_id=current_user.id)
            db.session.add(new_project)
            db.session.commit()
        return redirect(url_for('main.home'))
    # The create.html is now a generic "new project" page if no project is passed.
    return render_template("create.html", project=None)

@bp.route("/project/<int:project_id>")
@login_required
def manage_project(project_id):
    project = Project.query.get_or_404(project_id)
    # Check if user is owner or has shared access
    if project.user_id != current_user.id and current_user not in project.shared_with:
        abort(403)

    # Get all requirements with ALL versions (not just the latest)
    # Filter out deleted requirements
    requirements = (
        Requirement.query
        .filter_by(project_id=project_id, is_deleted=False)
        .all()
    )
    
    # For each requirement, get all versions
    req_with_versions = []
    for req in requirements:
        # Get all versions for this requirement
        versions = req.versions
        if versions:  # Only include requirements that have versions
            req_with_versions.append((req, versions))
    
    # Get custom columns for this project
    custom_columns = project.get_custom_columns()
    
    selected_version_id = request.args.get("selected_version_id", type=int)

    return render_template(
        "create.html", 
        project=project, 
        req_with_versions=req_with_versions,
        custom_columns=custom_columns,
        selected_version_id=selected_version_id
    )

@bp.route("/deleted_requirements")
@login_required
def deleted_requirements_overview():
    """Show all deleted requirements across all user's projects."""
    projects = Project.query.filter_by(user_id=current_user.id).all()
    
    # Collect deleted requirements from all projects
    all_deleted = []
    for project in projects:
        deleted_reqs = Requirement.query.filter_by(
            project_id=project.id, 
            is_deleted=True
        ).all()
        
        for req in deleted_reqs:
            latest_version = req.get_latest_version()
            if latest_version:
                all_deleted.append({
                    'project': project,
                    'requirement': req,
                    'version': latest_version
                })
    
    return render_template(
        "deleted_requirements_overview.html",
        deleted_items=all_deleted
    )

@bp.route("/requirement/<int:rid>/history")
@login_required
def requirement_history(rid):
    from .models import RequirementVersionHistory
    
    req = Requirement.query.get_or_404(rid)
    # Authorization check: ensure the user has access to the project (owner or shared)
    check_requirement_access(req)
    
    # Get latest version
    latest_version = req.get_latest_version()
    if not latest_version:
        flash("No versions found for this requirement.", "warning")
        return redirect(url_for('main.manage_project', project_id=req.project_id))
    
    # Get all history entries for this version (ordered by date)
    history_entries = RequirementVersionHistory.query.filter_by(
        version_id=latest_version.id
    ).order_by(RequirementVersionHistory.created_at.asc()).all()
    
    # Build timeline: creation + all modifications
    timeline = []
    
    # Add creation entry
    if latest_version.created_by:
        timeline.append({
            'type': 'created',
            'user': latest_version.created_by,
            'timestamp': latest_version.created_at,
            'changes': {'action': 'Version erstellt'}
        })
    
    # Add all modification entries
    for entry in history_entries:
        timeline.append({
            'type': entry.change_type,
            'user': entry.changed_by,
            'timestamp': entry.created_at,
            'changes': entry.get_changes()
        })
    
    return render_template("requirement_history.html", 
                         req=req, 
                         version=latest_version,
                         timeline=timeline)


@bp.route("/project/delete/<int:project_id>", methods=['POST'])
@login_required
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)
    check_project_access(project)
    # Remove any active sessions for this project first to avoid
    # SQLAlchemy attempting to nullify the foreign key on ActiveSession
    # (the `project_id` column is NOT NULL).
    from .models import ActiveSession
    try:
        # Use a bulk delete to remove any active session rows referencing
        # this project. This issues a direct DELETE statement.
        ActiveSession.query.filter_by(project_id=project_id).delete()
    except Exception:
        # If something goes wrong, continue and let the later delete/commit
        # raise the appropriate error so it can be debugged.
        pass

    db.session.delete(project)
    db.session.commit()
    flash(f"Project '{project.name}' has been deleted.", "success")
    return redirect(url_for('main.home'))


# The routes below are now obsolete due to the data model refactoring
# and have been removed:
# - /project/<int:project_id>/deleted
# - /deleted_requirements_overview
# - /move/<int:project_id>/<int:req_id>/<string:from_table>/<string:to_table>
# - /edit/<int:project_id>/<int:req_id>
# - /export/<int:project_id>/<string:format>
# - /delete_column/<int:project_id>
# - /delete_requirement_permanently/<int:project_id>/<int:req_id>
# The simple /requirements and /add_requirement routes were also based on the old model.

# Routes for dynamic columns
@bp.route("/project/<int:project_id>/add_column", methods=['POST'])
@login_required
def add_column(project_id):
    project = Project.query.get_or_404(project_id)
    check_project_access(project)
    
    column_name = request.form.get('column_name', '').strip()
    if not column_name:
        flash("Column name cannot be empty.", "danger")
        return redirect(url_for('main.manage_project', project_id=project_id))
    
    # Get current columns and add the new one
    columns = project.get_custom_columns()
    if column_name in columns:
        flash(f"Column '{column_name}' already exists.", "warning")
    else:
        columns.append(column_name)
        project.set_custom_columns(columns)
        db.session.commit()
        flash(f"Column '{column_name}' added successfully.", "success")
    
    return redirect(url_for('main.manage_project', project_id=project_id))

@bp.route("/project/<int:project_id>/remove_column/<column_name>", methods=['POST'])
@login_required
def remove_column(project_id, column_name):
    project = Project.query.get_or_404(project_id)
    check_project_access(project)
    
    # Protected columns that cannot be deleted (ID and Version are database columns, not custom columns)
    PROTECTED_COLUMNS = ['title', 'description', 'category', 'status', 'titel', 'beschreibung', 'kategorie', 'id', 'version', 'ver', 'version_label', 'version_index']
    
    if column_name.lower() in [c.lower() for c in PROTECTED_COLUMNS]:
        flash(f"Die Spalte '{column_name}' ist geschützt und kann nicht gelöscht werden.", "danger")
        return redirect(url_for('main.manage_project', project_id=project_id))
    
    # Get current columns and remove the specified one
    columns = project.get_custom_columns()
    if column_name in columns:
        columns.remove(column_name)
        project.set_custom_columns(columns)
        db.session.commit()
        flash(f"Column '{column_name}' removed successfully.", "success")
    else:
        flash(f"Column '{column_name}' not found.", "warning")
    
    return redirect(url_for('main.manage_project', project_id=project_id))

# Route to update custom column data for a requirement version
@bp.route("/requirement_version/<int:version_id>/update_custom_data", methods=['POST'])
@login_required
def update_custom_data(version_id):
    version = RequirementVersion.query.get_or_404(version_id)
    # Authorization check
    check_version_access(version)
    
    column_name = request.form.get('column_name')
    value = request.form.get('value', '').strip()
    
    # Get current custom data and update it
    custom_data = version.get_custom_data()
    custom_data[column_name] = value
    version.set_custom_data(custom_data)
    db.session.commit()
    
    return jsonify({'success': True})

# Route to update requirement status
@bp.route("/requirement_version/<int:version_id>/update_status", methods=['POST'])
@login_required
def update_status(version_id):
    version = RequirementVersion.query.get_or_404(version_id)
    # Authorization check
    check_version_access(version)
    
    status = request.form.get('status')
    if status in ['Entwurf', 'In Bearbeitung', 'Freigabe', 'Verworfen']:
        version.status = status
        db.session.commit()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.accept_mimetypes.accept_json:
             return jsonify({'success': True, 'status': status, 'color': version.get_status_color()})
             
        flash(f"Status updated to '{status}'.", "success")
    else:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.accept_mimetypes.accept_json:
             return jsonify({'success': False, 'error': 'Invalid status'}), 400
        flash("Invalid status value.", "danger")
    
    return redirect(
        url_for(
            'main.manage_project',
            project_id=version.requirement.project_id,
            selected_version_id=version.id,
        )
    )


@bp.route("/project/<int:project_id>/kanban")
@login_required
def kanban_view(project_id):
    project = Project.query.get_or_404(project_id)
    check_project_access(project)

    # Get all active requirements
    requirements = Requirement.query.filter_by(project_id=project_id, is_deleted=False).all()
    
    # Sort into columns
    kanban_data = {
        'Entwurf': [],
        'In Bearbeitung': [],
        'Freigabe': []
    }
    
    for req in requirements:
        latest = req.get_latest_version()
        if latest and latest.status in kanban_data:
            kanban_data[latest.status].append({
                'req': req,
                'version': latest
            })
            
    custom_columns = project.get_custom_columns()
    
    return render_template(
        "kanban.html", 
        project=project, 
        kanban_data=kanban_data,
        custom_columns=custom_columns
    )


@bp.route("/project/<int:project_id>/requirements_status")
@login_required
def requirements_status_json(project_id):
    """API for live collaboration polling."""
    project = Project.query.get_or_404(project_id)
    check_project_access(project)
        
    requirements = Requirement.query.filter_by(project_id=project_id, is_deleted=False).all()
    status_list = []
    
    for req in requirements:
        latest = req.get_latest_version()
        if latest:
            status_list.append({
                'req_id': req.id,
                'version_id': latest.id,
                'is_blocked': latest.is_blocked,
                'blocked_by': latest.blocked_by.email if latest.blocked_by else None,
                'status': latest.status
            })
            
    return jsonify(status_list)

@bp.route("/project/<int:project_id>/heartbeat", methods=['POST'])
@login_required
def project_heartbeat(project_id):
    """Update user's presence in the project."""
    from .models import ActiveSession
    from datetime import datetime, timedelta
    
    project = Project.query.get_or_404(project_id)
    check_project_access(project)
    
    # Find or create active session
    session = ActiveSession.query.filter_by(
        user_id=current_user.id,
        project_id=project_id
    ).first()
    
    if session:
        session.last_seen = datetime.utcnow()
    else:
        session = ActiveSession(
            user_id=current_user.id,
            project_id=project_id,
            last_seen=datetime.utcnow()
        )
        db.session.add(session)
    
    db.session.commit()
    
    # Clean up old sessions (older than 30 seconds)
    threshold = datetime.utcnow() - timedelta(seconds=30)
    ActiveSession.query.filter(ActiveSession.last_seen < threshold).delete()
    db.session.commit()
    
    return jsonify({'ok': True})

@bp.route("/project/<int:project_id>/active_users")
@login_required
def active_users(project_id):
    """Get list of currently active users in the project."""
    from .models import ActiveSession, User
    from datetime import datetime, timedelta
    
    project = Project.query.get_or_404(project_id)
    check_project_access(project)
    
    # Get sessions active in last 30 seconds
    threshold = datetime.utcnow() - timedelta(seconds=30)
    active_sessions = ActiveSession.query.filter(
        ActiveSession.project_id == project_id,
        ActiveSession.last_seen >= threshold
    ).all()
    
    users_data = []
    for session in active_sessions:
        if session.user_id != current_user.id:  # Don't include current user
            users_data.append({
                'id': session.user.id,
                'email': session.user.email,
                'initials': ''.join([word[0].upper() for word in session.user.email.split('@')[0].split('.')[:2]])
            })
    
    return jsonify(users_data)


# AJAX route to get all versions of a requirement
@bp.route("/requirement/<int:req_id>/versions_json")
@login_required
def requirement_versions_json(req_id):
    req = Requirement.query.get_or_404(req_id)
    # Authorization check
    check_requirement_access(req)
    
    versions_data = []
    for ver in req.versions:
        versions_data.append({
            'id': ver.id,
            'version_index': ver.version_index,
            'version_label': ver.version_label,
            'title': ver.title,
            'description': ver.description,
            'category': ver.category,
            'status': ver.status,
            'status_color': ver.get_status_color(),
            'custom_data': ver.get_custom_data(),
            'created_at': ver.created_at.strftime('%Y-%m-%d %H:%M')
        })
    
    return jsonify(versions_data)


# AJAX route to get all revisions (snapshots) for a requirement
@bp.route("/requirement/<int:req_id>/revisions_json")
@login_required
def requirement_revisions_json(req_id):
    """Return revision snapshots scoped to a specific version (if provided)."""
    from .models import RequirementVersionHistory, RequirementVersion

    req = Requirement.query.get_or_404(req_id)
    check_requirement_access(req)

    version_id = request.args.get("version_id", type=int)

    # If no version_id provided, default to latest version to avoid mixing versions
    if version_id is None:
        latest = req.get_latest_version()
        version_id = latest.id if latest else None

    if not version_id:
        return jsonify([])

    version_obj = RequirementVersion.query.get_or_404(version_id)
    if version_obj.requirement_id != req.id:
        abort(404)

    history_entries = (
        RequirementVersionHistory.query
        .filter(
            RequirementVersionHistory.version_id == version_obj.id,
            RequirementVersionHistory.change_type == 'revised'
        )
        .order_by(RequirementVersionHistory.created_at.asc())
        .all()
    )

    revisions_data = []
    baseline_added = False

    for entry in history_entries:
        try:
            changes = entry.get_changes()
        except Exception:
            changes = {}

        baseline_snapshot = changes.get('revision_baseline')
        if baseline_snapshot and not baseline_added:
            revisions_data.append({
                'revision_label': baseline_snapshot.get('revision_label') or 'Entwurf',
                'revision_number': baseline_snapshot.get('revision_number') or 0,
                'version_label': baseline_snapshot.get('version_label'),
                'title': baseline_snapshot.get('title'),
                'description': baseline_snapshot.get('description'),
                'category': baseline_snapshot.get('category'),
                'status': baseline_snapshot.get('status'),
                'status_color': baseline_snapshot.get('status_color') or 'secondary',
                'custom_data': baseline_snapshot.get('custom_data') or {},
                'is_quantifiable': baseline_snapshot.get('is_quantifiable', False),
                'created_at': entry.created_at.isoformat()
            })
            baseline_added = True

    # Add fallback baseline when no baseline snapshot exists yet
    if not baseline_added:
        revisions_data.append({
            'revision_label': version_obj.revision or 'Entwurf',
            'revision_number': _roman_to_int(version_obj.revision),
            'version_label': version_obj.version_label,
            'title': version_obj.title,
            'description': version_obj.description,
            'category': version_obj.category,
            'status': version_obj.status,
            'status_color': version_obj.get_status_color(),
            'custom_data': version_obj.get_custom_data(),
            'is_quantifiable': version_obj.get_custom_data().get('is_quantifiable') in ['true', True],
            'created_at': version_obj.created_at.isoformat()
        })

    for entry in history_entries:
        try:
            changes = entry.get_changes()
        except Exception:
            changes = {}

        snapshot = changes.get('revision_snapshot') or {}
        if not snapshot:
            continue

        revisions_data.append({
            'revision_label': snapshot.get('revision_label'),
            'revision_number': snapshot.get('revision_number'),
            'version_label': snapshot.get('version_label'),
            'title': snapshot.get('title'),
            'description': snapshot.get('description'),
            'category': snapshot.get('category'),
            'status': snapshot.get('status'),
            'status_color': snapshot.get('status_color') or 'secondary',
            'custom_data': snapshot.get('custom_data') or {},
            'is_quantifiable': snapshot.get('is_quantifiable', False),
            'created_at': entry.created_at.isoformat()
        })

    return jsonify(revisions_data)

# Route to update requirement version data
@bp.route("/requirement_version/<int:version_id>/update", methods=['POST'])
@login_required
def update_requirement_version(version_id):
    from .models import RequirementVersionHistory
    import json
    
    version = RequirementVersion.query.get_or_404(version_id)
    # Authorization check
    check_version_access(version)
    
    # Get form data
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    category = request.form.get('category', '').strip()

    # Validate required fields
    if not title or not description:
        flash("Title and description are required.", "danger")
        return redirect(
            url_for(
                'main.manage_project',
                project_id=version.requirement.project_id,
                selected_version_id=version.id,
            )
        )
    
    # Track changes for history
    changes = {}
    if version.title != title:
        changes['title'] = f"{version.title} → {title}"
    if version.description != description:
        changes['description'] = "Beschreibung geändert"
    if (version.category or '') != category:
        changes['category'] = f"{version.category or '–'} → {category or '–'}"
    
    
    # Update fields
    version.title = title
    version.description = description
    version.category = category
    
    # Track who modified this version
    version.last_modified_by_id = current_user.id
    
    # Update custom data
    old_custom_data = version.get_custom_data()
    custom_data = old_custom_data.copy()
    project = version.requirement.project
    custom_columns = project.get_custom_columns()
    
    for column in custom_columns:
        value = request.form.get(f'custom_{column}', '').strip()
        old_value = custom_data.get(column, '')
        if old_value != value:
            changes[f'custom_{column}'] = f"{old_value or '–'} → {value or '–'}"
        custom_data[column] = value
    
    # Handle quantifiable checkbox
    old_quantifiable = old_custom_data.get('is_quantifiable', 'false')
    is_quantifiable = request.form.get('is_quantifiable') == 'on'
    new_quantifiable = 'true' if is_quantifiable else 'false'
    if old_quantifiable != new_quantifiable:
        changes['is_quantifiable'] = f"{'Ja' if old_quantifiable == 'true' else 'Nein'} → {'Ja' if is_quantifiable else 'Nein'}"
    custom_data['is_quantifiable'] = new_quantifiable
    
    # Save all custom data including is_quantifiable
    version.set_custom_data(custom_data)

    # Status nur automatisch setzen, wenn nicht explizit geändert
    old_status = version.status
    status_from_form = request.form.get('status')
    if status_from_form and status_from_form in ['Entwurf', 'In Bearbeitung', 'Freigabe', 'Verworfen']:
        if old_status != status_from_form:
            changes['status'] = f"{old_status} → {status_from_form}"
        version.status = status_from_form
    elif changes:
        new_status = 'In Bearbeitung'
        if old_status != new_status:
            changes['status'] = f"{old_status} → {new_status}"
        version.status = new_status
    else:
        version.status = old_status
    
    # Create history entry if there are changes
    if changes:
        history_entry = RequirementVersionHistory(
            version_id=version.id,
            changed_by_id=current_user.id,
            change_type='modified',
            changes=json.dumps(changes)
        )
        db.session.add(history_entry)
    
    # Save changes
    db.session.commit()
    
    # Create notifications for requirement update
    try:
        notify_requirement_updated(version, current_user)
    except Exception as e:
        # Don't fail the update if notification fails
        pass
    
    flash(f"Requirement updated successfully. Status: {version.status}", "success")
    return redirect(
        url_for(
            'main.manage_project',
            project_id=version.requirement.project_id,
            selected_version_id=version.id,
        )
    )


@bp.route("/requirement_version/<int:version_id>/revise", methods=['POST'])
@login_required
def revise_requirement_version(version_id):
    """Handle revision updates with revision numbering logic."""
    from .models import RequirementVersionHistory
    import json

    version = RequirementVersion.query.get_or_404(version_id)
    check_version_access(version)

    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    category = request.form.get('category', '').strip()
    revision_number = request.form.get('revision_number', type=int)

    if not title or not description:
        flash("Title and description are required for a Revision.", "danger")
        return redirect(
            url_for(
                'main.manage_project',
                project_id=version.requirement.project_id,
                selected_version_id=version.id,
            )
        )

    allowed_status = ['Entwurf', 'In Bearbeitung', 'Freigabe', 'Verworfen']
    status_from_form = request.form.get('status')

    def status_color_for(value):
        mapping = {
            'Entwurf': 'danger',
            'In Bearbeitung': 'warning',
            'Freigabe': 'success',
            'Verworfen': 'dark',
        }
        return mapping.get(value, 'secondary')

    # Collect custom data from the form
    project = version.requirement.project
    custom_columns = project.get_custom_columns()
    old_custom_data = version.get_custom_data()
    custom_data = old_custom_data.copy()
    for column in custom_columns:
        value = request.form.get(f'custom_{column}', '').strip()
        custom_data[column] = value

    is_quantifiable = request.form.get('is_quantifiable') == 'on'
    custom_data['is_quantifiable'] = 'true' if is_quantifiable else 'false'

    # Load all revision history entries once (ordered)
    history_entries = RequirementVersionHistory.query.filter_by(
        version_id=version.id, change_type='revised'
    ).order_by(RequirementVersionHistory.created_at.asc()).all()

    def find_revision_entry(target_number):
        for entry in history_entries:
            try:
                snapshot = (entry.get_changes() or {}).get('revision_snapshot') or {}
                if snapshot.get('revision_number') is not None and int(snapshot['revision_number']) == int(target_number):
                    return entry, snapshot
            except Exception:
                continue
        return None, None

    # Gather existing revision numbers to identify the latest
    existing_numbers = []
    for entry in history_entries:
        try:
            snapshot = (entry.get_changes() or {}).get('revision_snapshot') or {}
            if snapshot.get('revision_number') is not None:
                existing_numbers.append(int(snapshot['revision_number']))
        except Exception:
            continue
    current_number = _roman_to_int(version.revision)
    if current_number:
        existing_numbers.append(current_number)
    latest_number = max(existing_numbers) if existing_numbers else 0

    def build_snapshot(target_status, target_revision_number):
        return {
            "title": title,
            "description": description,
            "category": category,
            "status": target_status,
            "status_color": status_color_for(target_status),
            "custom_data": custom_data,
            "is_quantifiable": is_quantifiable,
            "version_label": version.version_label,
            "revision_label": _int_to_roman(target_revision_number) if target_revision_number else (version.revision or 'Entwurf'),
            "revision_number": target_revision_number if target_revision_number else _roman_to_int(version.revision),
        }

    # CASE 1: Update an existing revision (revision_number provided)
    if revision_number is not None:
        target_entry, existing_snapshot = find_revision_entry(revision_number)
        if not target_entry:
            # If the requested revision doesn't exist yet, fall back to creating a new one
            revision_number = None
        else:
            prev_custom = existing_snapshot.get('custom_data') or {}
            prev_status = existing_snapshot.get('status') or version.status

            target_status = status_from_form if status_from_form in allowed_status else prev_status

            # Detect changes relative to the selected revision snapshot
            changes_detected = False
            def changed(old_val, new_val):
                return (old_val or "") != (new_val or "")

            if changed(existing_snapshot.get('title'), title):
                changes_detected = True
            if changed(existing_snapshot.get('description'), description):
                changes_detected = True
            if changed(existing_snapshot.get('category'), category):
                changes_detected = True
            for column in custom_columns:
                if changed(prev_custom.get(column, ''), custom_data.get(column, '')):
                    changes_detected = True
            if changed(prev_status, target_status):
                changes_detected = True
            if changed(
                str(existing_snapshot.get('is_quantifiable', False)),
                str(is_quantifiable),
            ):
                changes_detected = True

            if not changes_detected:
                flash("Keine Änderungen erkannt. Nimm Änderungen vor, bevor du revidierst.", "warning")
                return redirect(
                    url_for(
                        'main.manage_project',
                        project_id=version.requirement.project_id,
                        selected_version_id=version.id,
                    )
                )

            new_snapshot = build_snapshot(target_status, revision_number)
            changes = target_entry.get_changes() or {}
            changes['revision_snapshot'] = new_snapshot
            changes['revision'] = f"Revision {_int_to_roman(revision_number)} aktualisiert"
            target_entry.changes = json.dumps(changes)

            # Only push the edited values onto the live version when editing the latest revision
            if revision_number >= latest_number:
                version.title = title
                version.description = description
                version.category = category
                version.last_modified_by_id = current_user.id
                version.set_custom_data(custom_data)
                if target_status in allowed_status:
                    version.status = target_status
                version.revision = _int_to_roman(revision_number)

            db.session.commit()

            flash(
                f"Revision {_int_to_roman(revision_number)} wurde aktualisiert.",
                "success",
            )
            return redirect(
                url_for(
                    'main.manage_project',
                    project_id=version.requirement.project_id,
                    selected_version_id=version.id,
                )
            )

    # CASE 2: Create a new revision (existing behavior)
    # Preserve old state for baseline snapshot (before first revision)
    old_state_snapshot = {
        "title": version.title,
        "description": version.description,
        "category": version.category,
        "status": version.status,
        "status_color": version.get_status_color(),
        "custom_data": version.get_custom_data(),
        "is_quantifiable": version.get_custom_data().get('is_quantifiable') in ['true', True],
        "version_label": version.version_label,
        "revision_label": version.revision or 'Entwurf',
        "revision_number": _roman_to_int(version.revision),
    }

    changes = {}
    if version.title != title:
        changes['title'] = f"{version.title} → {title}"
    if version.description != description:
        changes['description'] = "Beschreibung geändert"
    if (version.category or '') != category:
        changes['category'] = f"{version.category or '–'} → {category or '–'}"

    for column in custom_columns:
        old_value = old_custom_data.get(column, '')
        new_value = custom_data.get(column, '')
        if (old_value or '') != (new_value or ''):
            changes[f'custom_{column}'] = f"{old_value or '–'} → {new_value or '–'}"

    old_quantifiable = old_custom_data.get('is_quantifiable', 'false')
    new_quantifiable = custom_data.get('is_quantifiable', 'false')
    if old_quantifiable != new_quantifiable:
        changes['is_quantifiable'] = f"{'Ja' if old_quantifiable == 'true' else 'Nein'} → {'Ja' if new_quantifiable == 'true' else 'Nein'}"

    old_status = version.status
    if status_from_form and status_from_form in allowed_status:
        if old_status != status_from_form:
            changes['status'] = f"{old_status} → {status_from_form}"
        version.status = status_from_form
    elif changes:
        if old_status != 'In Bearbeitung':
            changes['status'] = f"{old_status} → In Bearbeitung"
        version.status = 'In Bearbeitung'

    if not changes:
        flash("Keine Änderungen erkannt. Nimm Änderungen vor, bevor du revidierst.", "warning")
        return redirect(
            url_for(
                'main.manage_project',
                project_id=version.requirement.project_id,
                selected_version_id=version.id,
            )
        )

    # Persist field updates for the latest revision path
    version.title = title
    version.description = description
    version.category = category
    version.last_modified_by_id = current_user.id
    version.set_custom_data(custom_data)

    existing_numbers_new = existing_numbers.copy()
    next_revision_number = (max(existing_numbers_new) if existing_numbers_new else 0) + 1
    version.revision = _int_to_roman(next_revision_number)

    snapshot = build_snapshot(version.status, next_revision_number)

    if next_revision_number == 1:
        changes['revision_baseline'] = old_state_snapshot

    changes['revision'] = f"Revision {version.revision} auf Version {version.version_label} gesetzt"
    changes['revision_snapshot'] = snapshot
    history_entry = RequirementVersionHistory(
        version_id=version.id,
        changed_by_id=current_user.id,
        change_type='revised',
        changes=json.dumps(changes)
    )
    db.session.add(history_entry)

    db.session.commit()

    flash(
        f"Revision {version.revision} wurde auf Version {version.version_label} gesetzt.",
        "success",
    )
    return redirect(
        url_for(
            'main.manage_project',
            project_id=version.requirement.project_id,
            selected_version_id=version.id,
        )
    )

# Route to toggle quantifiable status
@bp.route("/requirement_version/<int:version_id>/toggle_quantifiable", methods=['POST'])
@login_required
def toggle_quantifiable(version_id):
    from .models import RequirementVersionHistory
    import json
    
    version = RequirementVersion.query.get_or_404(version_id)
    check_version_access(version)
    
    custom_data = version.get_custom_data()
    current_value = custom_data.get('is_quantifiable', 'false')
    old_value = 'Ja' if (current_value == 'true' or current_value is True) else 'Nein'
    
    # Toggle value
    if current_value == 'true' or current_value is True:
        custom_data['is_quantifiable'] = 'false'
        new_value = 'Nein'
    else:
        custom_data['is_quantifiable'] = 'true'
        new_value = 'Ja'
    
    version.set_custom_data(custom_data)
    version.last_modified_by_id = current_user.id
    # Status auf 'In Bearbeitung' setzen
    version.status = 'In Bearbeitung'
    
    # Create history entry
    history_entry = RequirementVersionHistory(
        version_id=version.id,
        changed_by_id=current_user.id,
        change_type='modified',
        changes=json.dumps({'is_quantifiable': f"{old_value} → {new_value}"})
    )
    db.session.add(history_entry)
    db.session.commit()
    
    return redirect(
        url_for(
            'main.manage_project',
            project_id=version.requirement.project_id,
            selected_version_id=version.id,
        )
    )

# Route to delete a specific version of a requirement
@bp.route("/requirement_version/<int:version_id>/delete", methods=['POST'])
@login_required
def delete_requirement_version(version_id):
    version = RequirementVersion.query.get_or_404(version_id)
    req = version.requirement

    # Authorization check
    check_requirement_access(req)

    project_id = req.project_id

    # Check if there are any remaining versions
    remaining_versions = RequirementVersion.query.filter_by(requirement_id=req.id).count()

    if remaining_versions == 1:
        # This is the last version, mark the requirement as deleted instead of deleting the version
        req.is_deleted = True
        flash("Last version deleted. Requirement moved to trash.", "success")
    else:
        # Delete this specific version
        db.session.delete(version)
        flash(f"Version {version.version_label} deleted successfully.", "success")

    db.session.commit()

    return redirect(url_for('main.deleted_requirements_overview'))

# Route to soft delete a requirement (kept for compatibility, but marks all versions as deleted)
@bp.route("/requirement/<int:req_id>/delete", methods=['POST'])
@login_required
def delete_requirement(req_id):
    req = Requirement.query.get_or_404(req_id)
    # Authorization check
    check_requirement_access(req)

    # Soft delete
    req.is_deleted = True
    db.session.commit()

    flash("Requirement moved to trash.", "success")
    return redirect(url_for('main.deleted_requirements_overview'))

# Route to restore a deleted requirement
@bp.route("/requirement/<int:req_id>/restore", methods=['POST'])
@login_required
def restore_requirement(req_id):
    req = Requirement.query.get_or_404(req_id)
    # Authorization check
    check_requirement_access(req)
    
    # Restore
    req.is_deleted = False
    db.session.commit()
    
    flash("Requirement restored successfully.", "success")
    return redirect(url_for('main.deleted_requirements_overview'))

# Route to permanently delete a requirement
@bp.route("/requirement/<int:req_id>/delete_permanently", methods=['POST'])
@login_required
def delete_requirement_permanently(req_id):
    req = Requirement.query.get_or_404(req_id)
    # Authorization check
    check_requirement_access(req)
    
    project_id = req.project_id
    
    # Permanently delete (cascade will delete all versions)
    db.session.delete(req)
    db.session.commit()
    
    flash("Requirement permanently deleted.", "success")
    return redirect(url_for('main.deleted_requirements_overview'))

# Route to regenerate a single requirement with AI
@bp.route("/requirement/<int:req_id>/regenerate", methods=['POST'])
@login_required
def regenerate_requirement(req_id):
    req = Requirement.query.get_or_404(req_id)
    # Authorization check
    check_requirement_access(req)
    
    # Get the latest version to use as context
    latest_version = req.get_latest_version()
    if not latest_version:
        flash("No existing version found to regenerate.", "danger")
        return redirect(url_for('main.manage_project', project_id=req.project_id))
    
    try:
        # Get project's custom columns
        custom_columns = req.project.get_custom_columns()
        
        # Prepare context for AI
        context = {
            "project_name": req.project.name,
            "requirement_title": latest_version.title,
            "requirement_description": latest_version.description,
            "requirement_category": latest_version.category or "",
            "custom_data": latest_version.get_custom_data()
        }
        
        # Build complete columns list: title, description, custom columns, category
        columns = ["title", "description"] + custom_columns + ["category"]
        
        # Generate a new version with AI
        result = generate_single_requirement_alternative(context, columns)
        
        if not result:
            flash("Failed to generate alternative. AI returned empty result.", "danger")
            return redirect(url_for('main.manage_project', project_id=req.project_id))
        
        # Calculate next version
        next_index = latest_version.version_index + 1
        next_label = chr(ord('A') + (next_index - 1))
        
        # Create new version
        new_version = RequirementVersion(
            requirement_id=req.id,
            version_index=next_index,
            version_label=next_label,
            title=result.get("title", latest_version.title),
            description=result.get("description", latest_version.description),
            category=result.get("category", latest_version.category),
            status="Entwurf",  # New version starts as "Entwurf"
            revision="Entwurf",
            created_by_id=current_user.id  # Track who created this version
        )
        
        # Get custom data from AI result or copy from previous version
        custom_data = {}
        for col in custom_columns:
            # Try to get value from AI result first, fallback to previous version
            value = result.get(col, latest_version.get_custom_data().get(col, ""))
            if value:
                custom_data[col] = value
        
        if custom_data:
            new_version.set_custom_data(custom_data)
        
        db.session.add(new_version)
        db.session.flush()  # Get the ID for history entry
        
        # Create history entry for regeneration
        from .models import RequirementVersionHistory
        import json
        history_entry = RequirementVersionHistory(
            version_id=new_version.id,
            changed_by_id=current_user.id,
            change_type='created',
            changes=json.dumps({'action': 'Version regeneriert (KI)', 'version': next_label})
        )
        db.session.add(history_entry)
        db.session.commit()
        
        flash(f"New version {next_label} generated successfully!", "success")
        
    except Exception as e:
        flash(f"Error generating alternative: {str(e)}", "danger")
    
    return redirect(url_for('main.manage_project', project_id=req.project_id))

def generate_single_requirement_alternative(context, columns):
    """Generate an alternative version of a requirement using AI."""
    try:
        # Prepare prompt for AI
        prompt = f"""
        Generate an alternative version of the following requirement:
        
        Project: {context['project_name']}
        
        Original Requirement:
        Title: {context['requirement_title']}
        Description: {context['requirement_description']}
        Category: {context['requirement_category']}
        
        Additional Context:
        {context['custom_data']}
        
        Please provide an improved version with:
        1. A clearer title
        2. A more detailed description
        3. The same or improved category
        
        Keep the core meaning but enhance clarity, completeness, and precision.
        """
        
        # Call the AI service
        ai_result = generate_requirements(prompt, {}, columns)
        
        # We expect a list of requirements, but we only need the first one
        if ai_result and len(ai_result) > 0:
            return ai_result[0]
        
        return None
        
    except Exception as e:
        print(f"Error in generate_single_requirement_alternative: {str(e)}")
        raise

# Route to export project requirements to Excel
@bp.route("/project/<int:project_id>/export_excel")
@login_required
def export_excel(project_id):
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment
    from io import BytesIO
    from flask import send_file
    
    project = Project.query.get_or_404(project_id)
    check_project_access(project)
    
    # Get all non-deleted requirements with their latest versions
    requirements = Requirement.query.filter_by(
        project_id=project_id,
        is_deleted=False
    ).all()
    
    # Get custom columns
    custom_columns = project.get_custom_columns()
    
    # Create workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Requirements"
    
    # Define headers in requested order
    headers = [
        "Verantwortlicher",
        "Revision",
        "Version",
        "ID",
        "Anforderung",
        "Beschreibung",
    ] + custom_columns + ["Kategorie", "Status"]
    
    # Write headers
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num, value=header)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center", vertical="top")
    
    # Write data rows
    row_num = 2
    display_id = 1
    
    for req in requirements:
        latest_version = req.get_latest_version()
        if not latest_version:
            continue
        
        custom_data = latest_version.get_custom_data()
        
        # Prepare row data in requested order
        creator = latest_version.created_by.email if latest_version.created_by else "–"
        revision = latest_version.revision or "Entwurf"
        row_data = [
            creator,
            revision,
            latest_version.version_label,
            display_id,
            latest_version.title,
            latest_version.description,
        ]
        
        # Add custom column values
        for col in custom_columns:
            row_data.append(custom_data.get(col, "–"))
        
        # Add category and status
        row_data.append(latest_version.category or "–")
        row_data.append(latest_version.status)
        
        # Write row
        for col_num, value in enumerate(row_data, 1):
            cell = ws.cell(row=row_num, column=col_num, value=value)
            cell.alignment = Alignment(wrap_text=True, vertical="top")
        
        row_num += 1
        display_id += 1
    
    # Set column widths (readable layout)
    ws.column_dimensions['A'].width = 24  # Verantwortlicher
    ws.column_dimensions['B'].width = 12  # Revision
    ws.column_dimensions['C'].width = 10  # Version
    ws.column_dimensions['D'].width = 8   # ID
    ws.column_dimensions['E'].width = 35  # Anforderung
    ws.column_dimensions['F'].width = 60  # Beschreibung

    # Set widths for custom columns starting at column G
    col_letter_start = ord('G')
    for i, col in enumerate(custom_columns):
        col_letter = chr(col_letter_start + i)
        ws.column_dimensions[col_letter].width = 22

    # Set widths for category and status after custom columns
    col_letter = chr(col_letter_start + len(custom_columns))
    ws.column_dimensions[col_letter].width = 20  # Kategorie
    col_letter = chr(col_letter_start + len(custom_columns) + 1)
    ws.column_dimensions[col_letter].width = 15  # Status
    
    # Save to BytesIO
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    
    # Create filename
    filename = f"requirements_{project.name.replace(' ', '_')}.xlsx"
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )

# Route to import requirements from Excel
@bp.route("/project/<int:project_id>/import_excel", methods=['POST'])
@login_required
def import_excel(project_id):
    from openpyxl import load_workbook
    from werkzeug.utils import secure_filename
    import os
    
    project = Project.query.get_or_404(project_id)
    check_project_access(project)
    
    # Check if file was uploaded
    if 'excel_file' not in request.files:
        flash("Keine Datei ausgewählt.", "danger")
        return redirect(url_for('main.manage_project', project_id=project_id))
    
    file = request.files['excel_file']
    
    if file.filename == '':
        flash("Keine Datei ausgewählt.", "danger")
        return redirect(url_for('main.manage_project', project_id=project_id))
    
    if not file.filename.endswith(('.xlsx', '.xls')):
        flash("Bitte laden Sie eine Excel-Datei (.xlsx oder .xls) hoch.", "danger")
        return redirect(url_for('main.manage_project', project_id=project_id))
    
    try:
        # Load workbook
        wb = load_workbook(file, data_only=True)
        ws = wb.active
        
        # Get custom columns for this project
        custom_columns = project.get_custom_columns()
        
        # Read header row to map columns
        headers = []
        for cell in ws[1]:
            if cell.value:
                headers.append(str(cell.value).strip())
        
        # Find column indices
        title_idx = None
        description_idx = None
        category_idx = None
        status_idx = None
        custom_col_indices = {}
        
        for idx, header in enumerate(headers):
            header_lower = header.lower()
            if header_lower in ['title', 'titel']:
                title_idx = idx
            elif header_lower in ['description', 'beschreibung']:
                description_idx = idx
            elif header_lower in ['category', 'kategorie']:
                category_idx = idx
            elif header_lower in ['status']:
                status_idx = idx
            elif header in custom_columns:
                custom_col_indices[header] = idx
        
        if title_idx is None or description_idx is None:
            flash("Excel-Datei muss mindestens 'Title' und 'Beschreibung' Spalten enthalten.", "danger")
            return redirect(url_for('main.manage_project', project_id=project_id))
        
        # Import rows (skip header)
        imported_count = 0
        for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            if not row or len(row) <= title_idx:
                continue
            
            title = row[title_idx]
            if not title or str(title).strip() == '':
                continue
            
            title = str(title).strip()
            description = str(row[description_idx]).strip() if description_idx < len(row) and row[description_idx] else ""
            
            if not description:
                continue
            
            category = str(row[category_idx]).strip() if category_idx is not None and category_idx < len(row) and row[category_idx] else ""
            status = str(row[status_idx]).strip() if status_idx is not None and status_idx < len(row) and row[status_idx] else "Entwurf"
            
            # Validate status
            if status not in ['Entwurf', 'In Bearbeitung', 'Freigabe']:
                status = 'Entwurf'
            
            # Create requirement
            from .agent import normalize_key
            key = normalize_key(title)
            
            req = Requirement.query.filter_by(project_id=project_id, key=key).first()
            
            if not req:
                req = Requirement(project_id=project_id, key=key)
                db.session.add(req)
                db.session.flush()
                version_index = 1
                version_label = 'A'
            else:
                # Create new version
                last_version = req.versions[-1] if req.versions else None
                version_index = last_version.version_index + 1 if last_version else 1
                version_label = chr(ord('A') + (version_index - 1))
            
            # Create version
            new_version = RequirementVersion(
                requirement_id=req.id,
                version_index=version_index,
                version_label=version_label,
                title=title,
                description=description,
                category=category,
                status=status,
                created_by_id=current_user.id
            )
            
            # Add custom column data
            custom_data = {}
            for col_name, col_idx in custom_col_indices.items():
                if col_idx < len(row) and row[col_idx]:
                    custom_data[col_name] = str(row[col_idx]).strip()
            
            if custom_data:
                new_version.set_custom_data(custom_data)
            
            db.session.add(new_version)
            db.session.flush()  # Get the ID for history entry
            
            # Create history entry for import
            from .models import RequirementVersionHistory
            import json
            history_entry = RequirementVersionHistory(
                version_id=new_version.id,
                changed_by_id=current_user.id,
                change_type='created',
                changes=json.dumps({'action': 'Version importiert (Excel)', 'version': version_label})
            )
            db.session.add(history_entry)
            
            imported_count += 1
        
        db.session.commit()
        flash(f"{imported_count} Anforderungen erfolgreich importiert!", "success")
        
    except Exception as e:
        db.session.rollback()
        flash(f"Fehler beim Importieren: {str(e)}", "danger")
    
    return redirect(url_for('main.manage_project', project_id=project_id))

# Route to share project with another user
@bp.route("/project/<int:project_id>/share", methods=['POST'])
@login_required
def share_project(project_id):
    from .models import User
    
    project = Project.query.get_or_404(project_id)
    check_project_access(project)
    
    email = request.form.get('email', '').strip()
    if not email:
        flash("Bitte geben Sie eine E-Mail-Adresse ein.", "danger")
        return redirect(url_for('main.manage_project', project_id=project_id))
    
    # Find user by email
    user = User.query.filter_by(email=email).first()
    if not user:
        flash(f"Benutzer mit E-Mail '{email}' nicht gefunden.", "danger")
        return redirect(url_for('main.manage_project', project_id=project_id))
    
    if user.id == current_user.id:
        flash("Sie können das Projekt nicht mit sich selbst teilen.", "warning")
        return redirect(url_for('main.manage_project', project_id=project_id))
    
    # Check if already shared
    if user in project.shared_with:
        flash(f"Projekt ist bereits mit {email} geteilt.", "warning")
        return redirect(url_for('main.manage_project', project_id=project_id))
    
    # Share project
    project.shared_with.append(user)
    db.session.commit()
    
    flash(f"Projekt erfolgreich mit {email} geteilt!", "success")
    return redirect(url_for('main.manage_project', project_id=project_id))

# Route to unshare project
@bp.route("/project/<int:project_id>/unshare/<int:user_id>", methods=['POST'])
@login_required
def unshare_project(project_id, user_id):
    from .models import User
    
    project = Project.query.get_or_404(project_id)
    check_project_access(project)
    
    user = User.query.get_or_404(user_id)
    
    if user in project.shared_with:
        project.shared_with.remove(user)
        db.session.commit()
        flash(f"Projekt-Freigabe für {user.email} entfernt.", "success")
    else:
        flash("Benutzer hat keinen Zugriff auf dieses Projekt.", "warning")
    
    return redirect(url_for('main.manage_project', project_id=project_id))

# Route to toggle requirement version block status
@bp.route("/requirement_version/<int:version_id>/toggle_block", methods=['POST'])
@login_required
def toggle_block_requirement(version_id):
    from datetime import datetime
    
    version = RequirementVersion.query.get_or_404(version_id)
    project = version.requirement.project
    
    # Authorization check - only project owner can block
    if project.user_id != current_user.id:
        abort(403)
    
    # Toggle block status
    if version.is_blocked:
        # Unblock
        version.is_blocked = False
        version.blocked_by_id = None
        version.blocked_at = None
        flash(f"Version {version.version_label} wurde freigegeben.", "success")
    else:
        # Block
        version.is_blocked = True
        version.blocked_by_id = current_user.id
        version.blocked_at = datetime.utcnow()
        flash(f"Version {version.version_label} wurde blockiert.", "warning")
    
    db.session.commit()
    return redirect(
        url_for(
            'main.manage_project',
            project_id=project.id,
            selected_version_id=version.id,
        )
    )


@bp.route("/project/<int:project_id>/detect_conflicts")
@login_required
def detect_conflicts_route(project_id):
    from .services.ai_client import detect_conflicts
    
    project = Project.query.get_or_404(project_id)
    check_project_access(project)
        
    # Gather all latest versions of not deleted requirements
    # Similar logic to export/view
    requirements = Requirement.query.filter_by(
        project_id=project_id,
        is_deleted=False
    ).all()
    
    req_list = []
    display_id = 1
    
    for req in requirements:
        latest = req.get_latest_version()
        if latest:
            req_data = {
                "id": display_id, # User friendly ID
                "db_id": req.id,
                "title": latest.title,
                "description": latest.description
            }
            req_list.append(req_data)
            display_id += 1
            
    if len(req_list) < 2:
        return jsonify({'conflicts': []}) # Need at least 2 to have a conflict
        
    conflicts = detect_conflicts(req_list)
    
    return jsonify({'conflicts': conflicts})


@bp.route("/requirement_version/<int:version_id>/generate_tests", methods=['POST'])
@login_required
def generate_tests_route(version_id):
    from .services.ai_client import generate_test_cases
    
    version = RequirementVersion.query.get_or_404(version_id)
    try:
        check_version_access(version)
    except:
        return jsonify({'error': 'Zugriff verweigert'}), 403
        
    test_cases = generate_test_cases(version.title, version.description)
    return jsonify({'result': test_cases})


# ============================================================================
# Import Helper Functions for Comments and Notifications
# ============================================================================
from .utils.notifications import (
    notify_requirement_updated,
    notify_requirement_created,
    notify_comment_added,
    parse_mentions,
    find_user_by_mention
)

# ============================================================================
# Comment Routes
# ============================================================================

@bp.route("/requirement_version/<int:version_id>/comments", methods=['GET'])
@login_required
def get_comments(version_id):
    """Get all comments for a requirement version."""
    version = RequirementVersion.query.get_or_404(version_id)
    check_version_access(version)
    
    # Get all non-deleted comments, ordered by creation date
    comments = RequirementComment.query.filter_by(
        version_id=version_id,
        is_deleted=False
    ).order_by(RequirementComment.created_at.asc()).all()
    
    # Build comment tree
    comments_data = []
    for comment in comments:
        comment_data = {
            'id': comment.id,
            'text': comment.text,
            'author': {
                'id': comment.author.id,
                'email': comment.author.email,
                'name': comment.author.email.split('@')[0]
            },
            'created_at': comment.created_at.isoformat(),
            'updated_at': comment.updated_at.isoformat(),
            'parent_comment_id': comment.parent_comment_id,
            'replies': []
        }
        comments_data.append(comment_data)
    
    # Build tree structure
    comment_dict = {c['id']: c for c in comments_data}
    root_comments = []
    for comment in comments_data:
        if comment['parent_comment_id']:
            parent = comment_dict.get(comment['parent_comment_id'])
            if parent:
                parent['replies'].append(comment)
        else:
            root_comments.append(comment)
    
    return jsonify({'comments': root_comments})

@bp.route("/requirement_version/<int:version_id>/comments", methods=['POST'])
@login_required
def create_comment(version_id):
    """Create a new comment on a requirement version."""
    version = RequirementVersion.query.get_or_404(version_id)
    check_version_access(version)
    
    data = request.get_json()
    text = data.get('text', '').strip()
    parent_comment_id = data.get('parent_comment_id')  # Optional, for replies
    
    if not text:
        return jsonify({'error': 'Kommentar-Text ist erforderlich'}), 400
    
    # Validate parent comment if provided
    if parent_comment_id:
        parent = RequirementComment.query.get(parent_comment_id)
        if not parent or parent.version_id != version_id or parent.is_deleted:
            return jsonify({'error': 'Ungültiger Parent-Kommentar'}), 400
    
    # Create comment
    comment = RequirementComment(
        version_id=version_id,
        author_id=current_user.id,
        text=text,
        parent_comment_id=parent_comment_id
    )
    db.session.add(comment)
    db.session.commit()
    
    # Create notifications
    try:
        notify_comment_added(comment, current_user)
    except Exception as e:
        # Don't fail comment creation if notification fails
        pass
    
    # Return created comment
    return jsonify({
        'id': comment.id,
        'text': comment.text,
        'author': {
            'id': comment.author.id,
            'email': comment.author.email,
            'name': comment.author.email.split('@')[0]
        },
        'created_at': comment.created_at.isoformat(),
        'updated_at': comment.updated_at.isoformat(),
        'parent_comment_id': comment.parent_comment_id
    }), 201

@bp.route("/comment/<int:comment_id>", methods=['PUT'])
@login_required
def update_comment(comment_id):
    """Update an existing comment."""
    comment = RequirementComment.query.get_or_404(comment_id)
    check_version_access(comment.version)
    
    # Check if user is the author
    if comment.author_id != current_user.id:
        return jsonify({'error': 'Keine Berechtigung zum Bearbeiten dieses Kommentars'}), 403
    
    if comment.is_deleted:
        return jsonify({'error': 'Kommentar wurde gelöscht'}), 400
    
    data = request.get_json()
    text = data.get('text', '').strip()
    
    if not text:
        return jsonify({'error': 'Kommentar-Text ist erforderlich'}), 400
    
    comment.text = text
    db.session.commit()
    
    return jsonify({
        'id': comment.id,
        'text': comment.text,
        'updated_at': comment.updated_at.isoformat()
    })

@bp.route("/comment/<int:comment_id>", methods=['DELETE'])
@login_required
def delete_comment(comment_id):
    """Delete (soft delete) a comment."""
    comment = RequirementComment.query.get_or_404(comment_id)
    check_version_access(comment.version)
    
    # Check if user is the author or project owner
    project = comment.version.requirement.project
    if comment.author_id != current_user.id and project.user_id != current_user.id:
        return jsonify({'error': 'Keine Berechtigung zum Löschen dieses Kommentars'}), 403
    
    # Soft delete
    comment.is_deleted = True
    db.session.commit()
    
    return jsonify({'success': True})

# ============================================================================
# Notification Routes
# ============================================================================

@bp.route("/notifications", methods=['GET'])
@login_required
def get_notifications():
    """Get all notifications for current user."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    unread_only = request.args.get('unread_only', 'false').lower() == 'true'
    
    query = Notification.query.filter_by(user_id=current_user.id)
    if unread_only:
        query = query.filter_by(is_read=False)
    
    query = query.order_by(Notification.created_at.desc())
    
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    
    notifications = []
    for notif in paginated.items:
        metadata = notif.get_metadata()
        notifications.append({
            'id': notif.id,
            'type': notif.notification_type,
            'title': notif.title,
            'message': notif.message,
            'is_read': notif.is_read,
            'created_at': notif.created_at.isoformat(),
            'related_type': notif.related_type,
            'related_id': notif.related_id,
            'metadata': metadata
        })
    
    return jsonify({
        'notifications': notifications,
        'total': paginated.total,
        'page': page,
        'pages': paginated.pages,
        'unread_count': Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    })

@bp.route("/notifications/unread_count", methods=['GET'])
@login_required
def get_unread_notification_count():
    """Get count of unread notifications."""
    count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return jsonify({'unread_count': count})

@bp.route("/notification/<int:notification_id>/read", methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """Mark a notification as read."""
    notification = Notification.query.get_or_404(notification_id)
    
    if notification.user_id != current_user.id:
        return jsonify({'error': 'Keine Berechtigung'}), 403
    
    notification.mark_as_read()
    db.session.commit()
    
    return jsonify({'success': True})

@bp.route("/notifications/mark_all_read", methods=['POST'])
@login_required
def mark_all_notifications_read():
    """Mark all notifications as read for current user."""
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update(
        {'is_read': True, 'read_at': datetime.utcnow()}
    )
    db.session.commit()
    
    return jsonify({'success': True})

@bp.route("/requirement_version/<int:version_id>/info")
@login_required
def get_version_info(version_id):
    """Get basic info about a requirement version (for navigation)."""
    version = RequirementVersion.query.get_or_404(version_id)
    check_version_access(version)
    
    return jsonify({
        'requirement_id': version.requirement_id,
        'version_id': version.id,
        'project_id': version.requirement.project_id
    })

@bp.route("/hello")
def hello():
    return "Hello from Blueprint!"

@bp.route("/requirement/<int:req_id>/toggle_funktional", methods=["POST"])

@bp.route("/requirement/<int:req_id>/toggle_funktional", methods=["POST"])
@login_required
def toggle_funktional(req_id):
    from .models import RequirementVersionHistory

    req = Requirement.query.get_or_404(req_id)
    check_requirement_access(req)
    # Toggle Wert setzen
    new_value = request.form.get("funktional")
    old_value = req.funktional
    req.funktional = bool(int(new_value))
    latest_version = req.get_latest_version()
    if latest_version and old_value != req.funktional:
        latest_version.last_modified_by_id = current_user.id
        # Status auf 'In Bearbeitung' setzen
        latest_version.status = 'In Bearbeitung'
        history_entry = RequirementVersionHistory(
            version_id=latest_version.id,
            changed_by_id=current_user.id,
            change_type='modified',
            changes=json.dumps({
                'funktional': f"{'Ja' if old_value else 'Nein'} → {'Ja' if req.funktional else 'Nein'}"
            })
        )
        db.session.add(history_entry)
    db.session.commit()
    flash(
        f"Funktionalität für Anforderung #{req.id} wurde "
        f"{'aktiviert' if req.funktional else 'deaktiviert' }.",
        "success"
    )
    return redirect(request.referrer or url_for('main.manage_project', project_id=req.project_id))

@bp.route("/requirement_version/<int:version_id>/analyze", methods=['POST'])
@login_required
def analyze_requirement_route(version_id):
    from .services.ai_client import analyze_requirement

    version = RequirementVersion.query.get_or_404(version_id)
    try:
        check_version_access(version)
    except:
        return jsonify({'error': 'Zugriff verweigert'}), 403

    analysis = analyze_requirement(version.title, version.description, version.status)
    quantifiable = (
        analysis.get("quantifiable_assessment", {}).get("is_quantifiable") is True
    )

    status_value = (version.status or "").strip().lower()
    if status_value in {"freigabe"}:
        status_color = "GRÜN"
    elif status_value in {"in bearbeitung"}:
        status_color = "GELB"
    else:
        status_color = "ROT"

    analysis["status_context"] = {
        "status": version.status,
        "ampel": status_color if quantifiable else "NICHT_ANWENDBAR"
    }
    return jsonify({'result': analysis})

