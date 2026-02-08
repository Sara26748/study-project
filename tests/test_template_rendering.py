"""
Test script to verify template rendering
"""
from app import create_app, db
from app.models import Project, User
from flask import render_template_string

app = create_app()

with app.app_context():
    # Get a test project
    project = Project.query.first()
    if project:
        custom_columns = project.get_custom_columns()
        print(f"Project: {project.name}")
        print(f"Custom Columns: {custom_columns}")
        print(f"Custom Columns JSON: {custom_columns}")
        
        # Test Jinja2 rendering
        test_template = "{{ custom_columns|tojson|safe }}"
        from flask import render_template_string
        result = render_template_string(test_template, custom_columns=custom_columns)
        print(f"Rendered: {result}")
    else:
        print("No project found")
