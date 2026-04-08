import requests

# Test the admin dashboard page
url = "http://127.0.0.1:8000/dashboard/admin-dashboard/reports.html/"

try:
    response = requests.get(url, allow_redirects=False)
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    
    if response.status_code == 302:
        print(f"Redirect to: {response.headers.get('Location', 'Unknown')}")
    elif response.status_code == 200:
        content = response.text[:1000]  # First 1000 chars
        print("Page content preview:")
        print(content)
        
        # Check for key elements
        if "Agent Performance" in response.text:
            print("✓ Agent Performance section found")
        else:
            print("✗ Agent Performance section NOT found")
            
        if "ratings_agent_perf" in response.text:
            print("✓ ratings_agent_perf template variable found")
        else:
            print("✗ ratings_agent_perf template variable NOT found")
    
except Exception as e:
    print(f"Error: {e}")
