#!/usr/bin/env python
import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.template import Template, Context
from django.contrib.auth.models import User

def test_template_rendering():
    print("=== Test Template Rendering ===")
    
    # Create a simple template with the priority chart
    template_content = '''
    <canvas id="tickets-by-priority-chart"></canvas>
    <script>
        const priorityData = {{ agent_report_priority_counts_json|safe }};
        console.log('Priority data:', priorityData);
    </script>
    '''
    
    # Create context with test data
    context = Context({
        'agent_report_priority_counts_json': '[0, 5, 0, 0]'
    })
    
    # Render template
    template = Template(template_content)
    rendered = template.render(context)
    
    print("Rendered template:")
    print(rendered)
    
    # Check if the JSON data is properly included
    if '[0, 5, 0, 0]' in rendered:
        print("✅ JSON data is properly included in template")
    else:
        print("❌ JSON data not found in template")

if __name__ == "__main__":
    test_template_rendering()
