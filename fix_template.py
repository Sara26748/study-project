# Script to fix the template
with open('app/templates/create.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the line
old_line = 'data-custom-data="{{ ver.get_custom_data()|tojson }}"'
new_line = 'data-custom-data="{{ ver.get_custom_data_json()|safe }}"'

content = content.replace(old_line, new_line)

with open('app/templates/create.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Template updated successfully!")
print(f"Replaced: {old_line}")
print(f"With: {new_line}")
