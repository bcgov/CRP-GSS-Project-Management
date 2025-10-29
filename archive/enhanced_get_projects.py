#!/usr/bin/env python3
"""
ArcGIS Online Data Access to return CRP projects 
"""

import requests
import json
from typing import List, Dict, Optional
from urllib.parse import urlencode
import os
import sys
from dotenv import load_dotenv

load_dotenv()

ARCGIS_ORG_ID = os.getenv('ARCGIS_ORG_ID')
GSS_PROJECT_URL = os.getenv('GSS_PROJECT_URL')
GSS_PROJECTS_TABLE_URL = os.getenv('GSS_PROJECTS_TABLE_URL')
GSS_RESOURCES_TABLE_URL = os.getenv('GSS_RESOURCES_TABLE_URL')
USERNAME = os.getenv('ARCGIS_USERNAME')
PASSWORD = os.getenv('ARCGIS_PASSWORD')
PORTAL_URL = os.getenv('ARCGIS_PORTAL_URL', 'https://www.arcgis.com/sharing/rest')
SEARCH_PERSON=os.getenv('PERSON')

class ArcGISOnlineClient:
    """Enhanced client for accessing ArcGIS Online services via REST API"""
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize the client
        
        Args:
            token: Authentication token (if required for private services)
        """
        self.token = token
        self.session = requests.Session()
    
    def generate_token(self, username: str, password: str, 
                      portal_url: str = None) -> str:
        """
        Generate authentication token
        
        Args:
            username: ArcGIS Online username
            password: ArcGIS Online password
            portal_url: Portal URL for token generation
            
        Returns:
            Authentication token
        """
        if portal_url is None:
            portal_url = PORTAL_URL
            
        token_url = f"{portal_url}/generateToken"
        
        params = {
            'username': username,
            'password': password,
            'client': 'referer',
            'referer': 'https://services6.arcgis.com',
            'f': 'json'
        }
        
        response = self.session.post(token_url, data=params)
        response.raise_for_status()
        
        result = response.json()
        if 'token' in result:
            self.token = result['token']
            return result['token']
        else:
            raise Exception(f"Token generation failed: {result}")
    
    def _make_request(self, url: str, params: Dict = None) -> Dict:
        """Make a request to ArcGIS REST API"""
        if params is None:
            params = {}
        
        if self.token:
            params['token'] = self.token
        
        params.update({
            'f': 'json',
            'outFields': '*'
        })
        
        try:
            headers = {'Referer': 'https://services6.arcgis.com'}
            response = self.session.get(url, params=params, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            if 'error' in result:
                raise Exception(f"ArcGIS API Error: {result['error']}")
            
            return result
        except requests.RequestException as e:
            print(f"Request failed: {e}")
            raise
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON response: {e}")
            raise
    
    def query_layer(self, service_url: str, where_clause: str = "1=1", 
                   return_geometry: bool = False, max_records: int = 1000) -> List[Dict]:
        """
        Query a feature layer or table
        
        Args:
            service_url: URL to the feature service layer
            where_clause: SQL where clause for filtering
            return_geometry: Whether to return geometry (for feature layers)
            max_records: Maximum number of records to return
            
        Returns:
            List of feature attributes
        """
        query_url = f"{service_url}/query"
        
        params = {
            'where': where_clause,
            'returnGeometry': 'true' if return_geometry else 'false',
            'spatialRel': 'esriSpatialRelIntersects',
            'outSR': '4326',
            'resultRecordCount': max_records
        }
        
        result = self._make_request(query_url, params)
        
        if 'features' in result:
            return [feature['attributes'] for feature in result['features']]
        else:
            print(f"No features found or error: {result}")
            return []
    
    def get_service_info(self, service_url: str) -> Dict:
        """Get information about a service"""
        return self._make_request(service_url)
    
    def find_matching_field(self, service_url: str, target_value: str) -> Optional[str]:
        """Find which field contains the target value by trying different field names"""
        possible_fields = ['Project_ID', 'Resource_Project_ID', 'ID', 'OBJECTID', 'GlobalID']
        
        print(f"Testing with sample value: {target_value}")
        
        for field_name in possible_fields:
            try:
                where_clause = f"{field_name} = '{target_value}'"
                result = self.query_layer(service_url, where_clause, max_records=1)
                if result:
                    print(f"✓ Found matching records using field '{field_name}'")
                    return field_name
                else:
                    print(f"✗ No records found using field '{field_name}'")
            except Exception as e:
                print(f"✗ Error with field '{field_name}': {str(e)[:100]}...")
        
        try:
            print("Getting sample record to see available fields...")
            sample = self.query_layer(service_url, "1=1", max_records=1)
            if sample:
                print(f"Available fields: {list(sample[0].keys())}")
        except Exception as e:
            print(f"Could not get sample record: {e}")
        
        return None

def search_resources_by_name(client: ArcGISOnlineClient, resources_url: str, 
                           resource_name: str) -> List[str]:
    """
    Search gss_resources table by Resource_Name and return Project_IDs 
    where Resource_Status is 'Assigned'
    """
    print(f"Searching for resource name: '{resource_name}'")
    print(f"Using URL: {resources_url}")
    
    escaped_name = resource_name.replace("'", "''")
    
    where_clause = f"Resource_Name = '{escaped_name}' AND Resource_Status = 'Assigned' AND Resource_Type='Coordinator'"
    print(f"Query: {where_clause}")
    
    try:
        resources = client.query_layer(resources_url, where_clause)
        print(f"Query returned {len(resources)} records")
        
        project_ids = []
        for resource in resources:
            if 'Resource_Project_ID' in resource and resource['Resource_Project_ID']:
                project_ids.append(str(resource['Resource_Project_ID']))
        
        print(f"Found {len(project_ids)} assigned projects for resource '{resource_name}'")
        if project_ids:
            print(f"Project IDs: {project_ids}")
        return list(set(project_ids)) 
        
    except Exception as e:
        print(f"Error searching resources: {e}")
        return []


def get_project_team_members(client: ArcGISOnlineClient, resources_url: str, 
                           project_ids: List[str]) -> Dict[str, List[Dict]]:
    """
    Get all team members assigned to the given projects where Resource_Type='Other'
    
    Args:
        client: ArcGIS Online client
        resources_url: URL to the gss_resources table
        project_ids: List of Project_IDs to look up team members for
        
    Returns:
        Dictionary mapping Project_ID to list of team member details
    """
    if not project_ids:
        return {}
    
    print(f"Looking up team members for {len(project_ids)} projects...")
    
    try:
        if len(project_ids) == 1:
            where_clause = f"Resource_Project_ID = '{project_ids[0]}' AND Resource_Type = 'Other' AND Resource_Status = 'Assigned'"
        else:
            project_ids_str = "','".join(project_ids)
            where_clause = f"Resource_Project_ID IN ('{project_ids_str}') AND Resource_Type = 'Other' AND Resource_Status = 'Assigned'"
        
        print(f"Team member query: {where_clause}")
        team_resources = client.query_layer(resources_url, where_clause)
        
        team_by_project = {}
        for resource in team_resources:
            project_id = resource.get('Resource_Project_ID')
            if project_id:
                if project_id not in team_by_project:
                    team_by_project[project_id] = []
                
                team_member = {
                    'Resource_Name': resource.get('Resource_Name'),
                    'Resource_Contact_Email': resource.get('Resource_Contact_Email'),
                    'Resource_Team': resource.get('Resource_Team'),
                    'Resource_Leadership': resource.get('Resource_Leadership')
                }
                team_by_project[project_id].append(team_member)
        
        total_team_members = sum(len(members) for members in team_by_project.values())
        print(f"Found {total_team_members} team members across {len(team_by_project)} projects")
        
        return team_by_project
        
    except Exception as e:
        print(f"Error getting team members: {e}")
        return {}

def get_project_details(client: ArcGISOnlineClient, projects_url: str, 
                       project_ids: List[str]) -> List[Dict]:
    """
    Get project details from gss_projects table using Project_ID field
    """
    if not project_ids:
        print("No project IDs provided")
        return []
    
    print(f"Looking up details for {len(project_ids)} projects")
    print(f"Using projects table URL: {projects_url}")
    
    try:
        if len(project_ids) == 1:
            where_clause = f"Project_ID = '{project_ids[0]}'"
        else:
            project_ids_str = "','".join(project_ids)
            where_clause = f"Project_ID IN ('{project_ids_str}')"
        
        print(f"Using query: {where_clause}")
        projects = client.query_layer(projects_url, where_clause, return_geometry=False)
        
        print(f"Retrieved details for {len(projects)} projects")
        return projects
        
    except Exception as e:
        print(f"Error getting project details: {e}")
        return []

def validate_service_url(client: ArcGISOnlineClient, url: str, service_name: str) -> bool:
    """Validate that a service URL is accessible"""
    try:
        info = client.get_service_info(url)
        print(f"✓ {service_name} service is accessible")
        return True
    except Exception as e:
        print(f"✗ {service_name} service not accessible: {e}")
        return False

def main():
    """Main function"""
    
    if not os.path.exists('.env'):
        print("❌ .env file not found!")
        print("Please create a .env file based on env_template")
        print("Copy env_template to .env and update with your actual values:")
        print("  cp env_template .env")
        return
    
    required_vars = ['GSS_PROJECT_URL', 'GSS_PROJECTS_TABLE_URL', 'GSS_RESOURCES_TABLE_URL']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables in .env file:")
        for var in missing_vars:
            print(f"   {var}")
        print("\nPlease update your .env file with the correct values")
        return
    
    client = ArcGISOnlineClient()
    
    if USERNAME and PASSWORD:
        try:
            print("Generating authentication token...")
            client.generate_token(USERNAME, PASSWORD)
            print("✓ Token generated successfully")
        except Exception as e:
            print(f"✗ Token generation failed: {e}")
            return
    else:
        print("❌ Username and password are required for authentication")
        print("Please update your .env file with ARCGIS_USERNAME and ARCGIS_PASSWORD")
        return
    
    service_urls = {
        'gss_project': GSS_PROJECT_URL,
        'gss_projects': GSS_PROJECTS_TABLE_URL,
        'gss_resources': GSS_RESOURCES_TABLE_URL
    }
    
    missing_urls = [name for name, url in service_urls.items() if not url or url == 'YOUR_ORG_ID' in url]
    if missing_urls:
        print(f"❌ Invalid service URLs in .env file: {', '.join(missing_urls)}")
        print("Please update your .env file with actual service URLs")
        if ARCGIS_ORG_ID and ARCGIS_ORG_ID != 'YOUR_ORG_ID':
            print(f"\nYour org ID is: {ARCGIS_ORG_ID}")
            print("Use the discover_services.py script to find your service URLs")
        return
    
    print("Validating service accessibility...")
    for name, url in service_urls.items():
        if not validate_service_url(client, url, name):
            print(f"Cannot proceed: {name} service is not accessible")
            return
        
    resource_name = SEARCH_PERSON
    
    if not resource_name:
        print("No resource name provided")
        return
    
    try:
        project_ids = search_resources_by_name(client, GSS_RESOURCES_TABLE_URL, resource_name)
        
        if not project_ids:
            print(f"No assigned projects found for resource '{resource_name}'")
            return
        
        print(f"Project IDs found: {', '.join(project_ids)}")
        
        project_details = get_project_details(client, GSS_PROJECTS_TABLE_URL, project_ids)
        
        if not project_details:
            print("No project details found")
            return
        
        team_members = get_project_team_members(client, GSS_RESOURCES_TABLE_URL, project_ids)
        
        for project in project_details:
            project_id = project.get('Project_ID')
            if project_id and project_id in team_members:
                project['Team_Members'] = team_members[project_id]
            else:
                project['Team_Members'] = []
        
        filtered_projects = []
        for project in project_details:
            project_name = project.get('Project_Name', '')
            if (project_name.startswith('CRP') or 
                project_name.startswith('crp') or 
                project_name.startswith('Caribou') or 
                project_name.startswith('caribou') or
                'Caribou' in project_name or
                'caribou' in project_name):
                filtered_projects.append(project)
        
        print(f"Filtered to {len(filtered_projects)} projects with CRP/Caribou names or containing 'Caribou'")
        
        if not filtered_projects:
            print("No projects match the criteria (must start with CRP/Caribou)")
            return
        
        project_details = filtered_projects
        
        print(f"\n{'='*60}")
        print(f"PROJECT DETAILS FOR RESOURCE: '{resource_name}'")
        print(f"{'='*60}")
        
        for i, project in enumerate(project_details, 1):
            print(f"\n--- Project {i} ---")
            
            for key, value in project.items():
                if key != 'Team_Members' and value is not None:
                    print(f"  {key}: {value}")
            
            team_members = project.get('Team_Members', [])
            if team_members:
                print(f"\n  Team Members ({len(team_members)}):")
                for j, member in enumerate(team_members, 1):
                    print(f"    {j}. {member.get('Resource_Name', 'N/A')}")
                    if member.get('Resource_Contact_Email'):
                        print(f"       Email: {member['Resource_Contact_Email']}")
                    if member.get('Resource_Team'):
                        print(f"       Team: {member['Resource_Team']}")
                    if member.get('Resource_Leadership'):
                        print(f"       Leadership: {member['Resource_Leadership']}")
            else:
                print(f"\n  Team Members: None (only coordinator assigned)")
        
        safe_filename = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in resource_name)
        output_file = f"projects_for_{safe_filename.replace(' ', '_')}.json"
        with open(output_file, 'w') as f:
            json.dump(project_details, f, indent=2, default=str)
        print(f" Results saved to: {output_file}")
        print(f" Found {len(project_details)} projects for resource '{resource_name}'")
        
    except Exception as e:
        print(f"Error occurred: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
