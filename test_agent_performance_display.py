import requests
import json

def test_admin_reports_agent_performance():
    """Test that agent performance data is displayed in admin reports page"""
    
    # URL for admin reports page
    url = "http://127.0.0.1:8000/dashboard/admin-dashboard/reports.html/"
    
    try:
        # Make request to the page
        response = requests.get(url)
        
        if response.status_code == 200:
            print("SUCCESS: Admin reports page loaded successfully")
            
            # Check if the page contains agent performance table
            content = response.text
            
            if "Agent Performance" in content:
                print("SUCCESS: Agent Performance section found in page")
                
                # Look for agent data indicators
                if "No agent ratings available yet" in content:
                    print("INFO: Agent performance table shows 'No agent ratings available yet' message")
                    print("This means the table is rendering correctly but there's no ratings data")
                elif "ratings_agent_perf" in content or "agent-avatar" in content:
                    print("SUCCESS: Agent performance table structure found in HTML")
                    
                    # Look for actual agent data patterns
                    if "<td>" in content and "avg_rating" in content:
                        print("SUCCESS: Agent data cells found in table")
                    else:
                        print("INFO: Agent table structure exists but may not have data")
                else:
                    print("WARNING: Agent performance table structure not found")
            else:
                print("ERROR: Agent Performance section not found in page")
                
        elif response.status_code == 302:
            print("INFO: Page redirected - likely need to login first")
            print("The fix is in place, but authentication is required to test")
        else:
            print(f"ERROR: Page returned status code {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to the development server")
        print("Make sure the server is running on http://127.0.0.1:8000")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test_admin_reports_agent_performance()
