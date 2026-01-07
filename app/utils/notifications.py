"""
Utility functions for creating notifications.
"""
from datetime import datetime
from .. import db
from ..models import Notification, User


def create_notification(user_id, notification_type, title, message=None, related_type=None, related_id=None, metadata=None):
    """Create a notification for a user."""
    notification = Notification(
        user_id=user_id,
        notification_type=notification_type,
        title=title,
        message=message,
        related_type=related_type,
        related_id=related_id
    )
    if metadata:
        notification.set_metadata(metadata)
    db.session.add(notification)
    return notification


def notify_requirement_updated(version, actor):
    """Notify project members when a requirement is updated."""
    project = version.requirement.project
    req_title = version.title[:50]  # Truncate for notification
    
    # Get all users with access to this project
    project_users = [project.user] + list(project.shared_with)
    
    # Create notifications for all users except the actor
    for user in project_users:
        if user.id != actor.id:
            create_notification(
                user_id=user.id,
                notification_type='requirement_updated',
                title=f'Anforderung aktualisiert: {req_title}',
                message=f'{actor.email.split("@")[0]} hat eine Anforderung in "{project.name}" aktualisiert.',
                related_type='requirement_version',
                related_id=version.id,
                metadata={'actor_id': actor.id, 'actor_email': actor.email, 'project_id': project.id}
            )
    
    db.session.commit()


def notify_requirement_created(version, actor):
    """Notify project members when a new requirement is created."""
    project = version.requirement.project
    req_title = version.title[:50]
    
    # Get all users with access to this project
    project_users = [project.user] + list(project.shared_with)
    
    for user in project_users:
        if user.id != actor.id:
            create_notification(
                user_id=user.id,
                notification_type='requirement_created',
                title=f'Neue Anforderung: {req_title}',
                message=f'{actor.email.split("@")[0]} hat eine neue Anforderung in "{project.name}" erstellt.',
                related_type='requirement_version',
                related_id=version.id,
                metadata={'actor_id': actor.id, 'actor_email': actor.email, 'project_id': project.id}
            )
    
    db.session.commit()


def parse_mentions(text):
    """Parse @mentions from text and return list of mentioned usernames/emails."""
    import re
    # Match @username or @email patterns
    mentions = re.findall(r'@(\w+(?:\.\w+)*@?\w*\.?\w*)', text)
    return list(set(mentions))  # Remove duplicates


def find_user_by_mention(mention, project):
    """Find user by mention (@username or @email) within project context."""
    # Try to find by email first (exact match)
    user = User.query.filter_by(email=mention).first()
    if user:
        # Check if user has access to project
        if project.user_id == user.id or user in project.shared_with:
            return user
    
    # Try to find by email prefix (before @)
    email_prefix = mention.split('@')[0] if '@' in mention else mention
    user = User.query.filter(User.email.like(f'{email_prefix}%')).first()
    if user and (project.user_id == user.id or user in project.shared_with):
        return user
    
    return None


def notify_comment_added(comment, actor):
    """Notify users when a comment is added (including @mentions)."""
    version = comment.version
    project = version.requirement.project
    req_title = version.title[:50]
    
    # Notify mentioned users
    mentions = parse_mentions(comment.text)
    for mention in mentions:
        mentioned_user = find_user_by_mention(mention, project)
        if mentioned_user and mentioned_user.id != actor.id:
            create_notification(
                user_id=mentioned_user.id,
                notification_type='mention',
                title=f'Du wurdest in einem Kommentar erwähnt: {req_title}',
                message=f'{actor.email.split("@")[0]} hat dich in einem Kommentar zu "{req_title}" erwähnt.',
                related_type='comment',
                related_id=comment.id,
                metadata={'actor_id': actor.id, 'actor_email': actor.email, 'project_id': project.id, 'requirement_version_id': version.id}
            )
    
    # Notify project members (except actor and already notified mentioned users)
    project_users = [project.user] + list(project.shared_with)
    mentioned_user_ids = {find_user_by_mention(m, project).id for m in mentions if find_user_by_mention(m, project)}
    
    for user in project_users:
        if user.id != actor.id and user.id not in mentioned_user_ids:
            create_notification(
                user_id=user.id,
                notification_type='comment',
                title=f'Neuer Kommentar: {req_title}',
                message=f'{actor.email.split("@")[0]} hat einen Kommentar zu "{req_title}" hinzugefügt.',
                related_type='comment',
                related_id=comment.id,
                metadata={'actor_id': actor.id, 'actor_email': actor.email, 'project_id': project.id, 'requirement_version_id': version.id}
            )
    
    db.session.commit()

