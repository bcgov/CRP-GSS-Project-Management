#!/usr/bin/env python3
"""
Enhanced Team Engagement Analysis for Caribou Recovery Program (CRP) Projects

This module provides comprehensive analysis of team engagement for projects that:
1. Start with "CRP" in the project name
2. Contain "Caribou" in the project name

Features:
- Query all CRP/Caribou projects from ArcGIS Online
- Analyze resource assignments and team member engagement
- Generate workload distribution and role-based analytics
- Provide top engaged team members summary

Author: Generated for Cole Folkers
Date: August 2025
"""

import requests
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
from dotenv import load_dotenv
import os
import sys
import importlib.util
from typing import List, Dict, Any, Optional


load_dotenv()

class TeamEngagementAnalyzer:
    """Analyzer for team engagement across CRP/Caribou projects"""
    
    def __init__(self):
        """Initialize the analyzer with ArcGIS client"""
        self.client = None
        self._initialize_arcgis_client()
    
    def _initialize_arcgis_client(self):
        """Initialize ArcGIS client using the same logic as enhanced_get_projects.py"""
        try:
            # Import the ArcGIS client from the working enhanced_get_projects.py
            spec = importlib.util.spec_from_file_location(
                "enhanced_get_projects", 
                "/home/cfolkers/caribou_portal/enhanced_get_projects.py"
            )
            enhanced_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(enhanced_module)
            
            # Use the same ArcGISOnlineClient class
            self.client = enhanced_module.ArcGISOnlineClient()
            
            # Get credentials from environment (same as enhanced_get_projects.py)
            username = os.getenv('ARCGIS_USERNAME')
            password = os.getenv('ARCGIS_PASSWORD')
            
            if username and password:
                print("Generating ArcGIS authentication token for team engagement analysis...")
                self.client.generate_token(username, password)
                print("✓ ArcGIS token generated successfully")
            else:
                print("❌ ArcGIS credentials not found in environment")
                print("Please ensure ARCGIS_USERNAME and ARCGIS_PASSWORD are set in .env file")
                self.client = None
                
        except Exception as e:
            print(f"Error initializing ArcGIS client for team engagement: {e}")
            import traceback
            traceback.print_exc()
            self.client = None
    
    def get_all_crp_projects(self) -> List[Dict]:
        """Get all CRP/Caribou projects from ArcGIS Online (current and completed)"""
        if not self.client:
            return []
        
        try:
            projects_url = os.getenv('GSS_PROJECTS_TABLE_URL')
            if not projects_url:
                print("GSS_PROJECTS_TABLE_URL not found in environment")
                return []
            
            print("Querying all projects from ArcGIS...")
            
            # Get ALL projects regardless of status (current and completed)
            all_projects = self.client.query_layer(projects_url, "1=1", max_records=2000)
            
            # Filter for CRP/Caribou projects by name
            crp_projects = []
            for project in all_projects:
                project_name = project.get('Project_Name', '')
                if (project_name.startswith('CRP') or 
                    'Caribou' in project_name or 
                    'caribou' in project_name):
                    crp_projects.append(project)
            
            print(f"Retrieved {len(all_projects)} total projects from ArcGIS")
            print(f"Filtered to {len(crp_projects)} CRP/Caribou projects (current and completed)")
            return crp_projects
            
        except Exception as e:
            print(f"Error getting CRP projects: {e}")
            return []
    
    def get_all_crp_resources(self, crp_projects: List[Dict]) -> List[Dict]:
        """Get all resource assignments for CRP/Caribou projects using Project_ID linkage"""
        if not self.client or not crp_projects:
            return []
        
        try:
            resources_url = os.getenv('GSS_RESOURCES_TABLE_URL')
            if not resources_url:
                print("GSS_RESOURCES_TABLE_URL not found in environment")
                return []
            
            # Extract Project_IDs from projects to link with resources (not GlobalID)
            project_ids = []
            for project in crp_projects:
                project_id = project.get('Project_ID')
                if project_id:
                    # Project_ID is the correct field for linking to resources
                    project_ids.append(str(project_id))
            
            if not project_ids:
                print("No Project_IDs found in projects")
                return []
            
            print(f"Querying resource assignments for {len(project_ids)} projects...")
            
            # Use smaller batches to avoid URL length issues
            all_resources = []
            batch_size = 10
            
            for i in range(0, len(project_ids), batch_size):
                batch_ids = project_ids[i:i + batch_size]
                
                if len(batch_ids) == 1:
                    where_clause = f"Resource_Project_ID = '{batch_ids[0]}' AND Resource_Status = 'Assigned'"
                else:
                    project_ids_str = "','".join(batch_ids)
                    where_clause = f"Resource_Project_ID IN ('{project_ids_str}') AND Resource_Status = 'Assigned'"
                
                print(f"Querying resources batch {i//batch_size + 1}: {len(batch_ids)} projects")
                try:
                    batch_resources = self.client.query_layer(resources_url, where_clause, max_records=1000)
                    all_resources.extend(batch_resources)
                    print(f"Retrieved {len(batch_resources)} resources from batch {i//batch_size + 1}")
                except Exception as e:
                    print(f"Error getting resources for batch {i//batch_size + 1}: {e}")
                    continue
            
            print(f"Found {len(all_resources)} total resource assignments for CRP projects")
            return all_resources
            
        except Exception as e:
            print(f"Error in get_all_crp_resources: {e}")
            return []
    
    def analyze_engagement_data(self) -> Dict[str, Any]:
        """
        Analyze engagement data and return summary by person
        
        Returns:
            Dictionary with engagement summary, total projects, total people, and any errors
        """
        try:
            # Check if client is available
            if not self.client:
                return {
                    'engagement_summary': {},
                    'total_projects': 0,
                    'total_people': 0,
                    'error': 'ArcGIS client not available. Check credentials and configuration.'
                }
            
            # Step 1: Get all CRP/Caribou projects (current and completed)
            print("Step 1: Getting all CRP/Caribou projects...")
            crp_projects = self.get_all_crp_projects()
            
            if not crp_projects:
                return {
                    'engagement_summary': {},
                    'total_projects': 0,
                    'total_people': 0,
                    'error': 'No CRP/Caribou projects found'
                }
            
            # Step 2: Get resource assignments using Project_ID linkage
            print("Step 2: Getting resource assignments...")
            crp_resources = self.get_all_crp_resources(crp_projects)
            
            # Step 3: Create project lookup by Project_ID for coordinator fallback
            print("Step 3: Building project coordinator lookup...")
            projects_by_project_id = {project.get('Project_ID'): project for project in crp_projects}
            
            # Step 4: Analyze engagement data with coordinator fallback logic
            print("Step 4: Analyzing engagement data...")
            engagement_by_person = defaultdict(lambda: {
                'total_projects': 0,
                'projects': [],
                'roles': set(),
                'project_statuses': defaultdict(int)
            })
            
            # Track which projects have assigned resources
            projects_with_resources = set()
            
            # Process assigned resources first
            for resource in crp_resources:
                person_name = resource.get('Resource_Name')
                project_id = resource.get('Resource_Project_ID')
                resource_type = resource.get('Resource_Type', 'Unknown')
                
                if person_name and project_id:
                    projects_with_resources.add(project_id)
                    
                    # Get project details
                    project = projects_by_project_id.get(project_id, {})
                    project_name = project.get('Project_Name', 'Unknown Project')
                    project_status = project.get('Project_Status', 'Unknown')
                    
                    engagement_by_person[person_name]['total_projects'] += 1
                    engagement_by_person[person_name]['projects'].append({
                        'name': project_name,
                        'project_id': project_id,
                        'status': project_status,
                        'role': resource_type
                    })
                    engagement_by_person[person_name]['roles'].add(resource_type)
                    engagement_by_person[person_name]['project_statuses'][project_status] += 1
            
            # Step 5: Apply coordinator fallback logic (only if no resources found)
            print("Step 5: Applying coordinator fallback logic...")
            for project in crp_projects:
                project_id = project.get('Project_ID')
                
                # If project has no assigned resources, assume coordinator is working on it
                if project_id and project_id not in projects_with_resources:
                    # Try to find the coordinator from project metadata
                    coordinator_name = None
                    
                    # Look for coordinator in various possible fields (excluding client fields)
                    possible_coordinator_fields = ['Project_Manager', 'Coordinator', 'Project_Lead', 'Lead_Scientist']
                    for field in possible_coordinator_fields:
                        if project.get(field):
                            coordinator_name = project.get(field)
                            break
                    
                    # If no coordinator found in metadata, skip this project
                    if coordinator_name:
                        project_name = project.get('Project_Name', 'Unknown Project')
                        project_status = project.get('Project_Status', 'Unknown')
                        
                        engagement_by_person[coordinator_name]['total_projects'] += 1
                        engagement_by_person[coordinator_name]['projects'].append({
                            'name': project_name,
                            'project_id': project_id,
                            'status': project_status,
                            'role': 'Coordinator (default)'
                        })
                        engagement_by_person[coordinator_name]['roles'].add('Coordinator (default)')
                        engagement_by_person[coordinator_name]['project_statuses'][project_status] += 1
            
            # Convert sets to lists for JSON serialization
            for person_data in engagement_by_person.values():
                person_data['roles'] = list(person_data['roles'])
            
            print(f"Step 6: Analysis complete!")
            print(f"  - {len(crp_projects)} CRP/Caribou projects found (current and completed)")
            print(f"  - {len(crp_resources)} resource assignments found")
            print(f"  - {len(projects_with_resources)} projects with explicit assignments")
            print(f"  - {len(crp_projects) - len(projects_with_resources)} projects using coordinator fallback")
            print(f"  - {len(engagement_by_person)} people engaged")
            
            return {
                'engagement_summary': engagement_by_person,
                'total_projects': len(crp_projects),
                'total_people': len(engagement_by_person),
                'error': None
            }
            
            if not project_ids:
                return {
                    'engagement_summary': {},
                    'total_projects': len(crp_projects),
                    'total_people': 0,
                    'error': 'No valid Project_IDs found in CRP/Caribou projects'
                }
            
            # Get all resource assignments
            print("Step 2: Getting resource assignments...")
            crp_resources = self.get_all_crp_resources(project_ids)
            
            if not crp_resources:
                return {
                    'engagement_summary': {},
                    'total_projects': len(crp_projects),
                    'total_people': 0,
                    'error': 'No resource assignments found for CRP/Caribou projects'
                }
            
            # Create project lookup for efficiency
            project_lookup = {str(p.get('Project_ID', '')): p for p in crp_projects}
            
            # Analyze by person
            print("Step 3: Analyzing engagement by person...")
            engagement_by_person = {}
            
            for resource in crp_resources:
                person_name = resource.get('Resource_Name', 'Unknown')
                project_id = str(resource.get('Resource_Project_ID', ''))
                resource_type = resource.get('Resource_Type', 'Unknown')
                
                # Skip if essential data is missing
                if not person_name or person_name == 'Unknown' or not project_id:
                    continue
                
                # Initialize person data if not exists
                if person_name not in engagement_by_person:
                    engagement_by_person[person_name] = {
                        'total_projects': 0,
                        'coordinator_projects': 0,
                        'team_member_projects': 0,
                        'projects': [],
                        'roles': set()
                    }
                
                person_data = engagement_by_person[person_name]
                
                # Check if this project is already counted for this person
                # (avoid double-counting if person has multiple roles on same project)
                existing_project_ids = [p['project_id'] for p in person_data['projects']]
                if project_id not in existing_project_ids:
                    person_data['total_projects'] += 1
                    
                    # Add project details
                    project_info = project_lookup.get(project_id, {})
                    person_data['projects'].append({
                        'project_id': project_id,
                        'project_name': project_info.get('Project_Name', 'Unknown'),
                        'project_number': project_info.get('Project_Number', 'N/A'),
                        'role': resource_type,
                        'project_status': project_info.get('Project_Status', 'Unknown')
                    })
                
                # Track roles
                person_data['roles'].add(resource_type)
                
                # Count by role type
                if resource_type == 'Coordinator':
                    person_data['coordinator_projects'] += 1
                else:
                    person_data['team_member_projects'] += 1
            
            # Convert sets to lists for JSON serialization
            for person in engagement_by_person:
                engagement_by_person[person]['roles'] = list(engagement_by_person[person]['roles'])
            
            print(f"Step 4: Analysis complete!")
            print(f"  - {len(crp_projects)} CRP/Caribou projects found")
            print(f"  - {len(crp_resources)} resource assignments found")
            print(f"  - {len(engagement_by_person)} people engaged")
            
            return {
                'engagement_summary': engagement_by_person,
                'total_projects': len(crp_projects),
                'total_people': len(engagement_by_person),
                'error': None
            }
            
        except Exception as e:
            print(f"Error analyzing engagement data: {e}")
            import traceback
            traceback.print_exc()
            return {
                'engagement_summary': {},
                'total_projects': 0,
                'total_people': 0,
                'error': str(e)
            }
    
    def get_workload_distribution(self, engagement_data: Dict) -> Dict[str, int]:
        """Analyze workload distribution by project count"""
        workload_counts = {}
        
        for person_name, person_data in engagement_data.items():
            total = person_data['total_projects']
            if total <= 1:
                category = '1 project'
            elif total <= 2:
                category = '2 projects'
            elif total <= 3:
                category = '3 projects'
            elif total <= 4:
                category = '4 projects'
            else:
                category = '5+ projects'
            
            workload_counts[category] = workload_counts.get(category, 0) + 1
        
        return workload_counts
    
    def get_role_distribution(self, engagement_data: Dict) -> Dict[str, int]:
        """Analyze role distribution across people"""
        role_stats = {'Coordinator': 0, 'Other': 0, 'Both': 0}
        
        for person_name, person_data in engagement_data.items():
            roles = person_data['roles']
            if 'Coordinator' in roles and 'Other' in roles:
                role_stats['Both'] += 1
            elif 'Coordinator' in roles:
                role_stats['Coordinator'] += 1
            else:
                role_stats['Other'] += 1
        
        return role_stats
    
    def get_top_engaged_people(self, engagement_data: Dict, limit: int = 10) -> List[tuple]:
        """Get the most engaged people sorted by project count"""
        return sorted(
            engagement_data.items(), 
            key=lambda x: x[1]['total_projects'], 
            reverse=True
        )[:limit]
    
    def validate_configuration(self) -> Dict[str, Any]:
        """Validate that all required configuration is available"""
        required_env_vars = [
            'GSS_PROJECTS_TABLE_URL', 
            'GSS_RESOURCES_TABLE_URL', 
            'ARCGIS_USERNAME', 
            'ARCGIS_PASSWORD'
        ]
        
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        
        return {
            'is_valid': len(missing_vars) == 0,
            'missing_vars': missing_vars,
            'client_available': self.client is not None
        }
    
    def analyze_client_engagement(self) -> Dict:
        """Analyze client engagement - how many CRP/Caribou projects each client has submitted"""
        try:
            print("Starting client engagement analysis...")
            
            # Get all CRP/Caribou projects
            print("Step 1: Getting all CRP/Caribou projects for client analysis...")
            crp_projects = self.get_all_crp_projects()
            
            if not crp_projects:
                return {
                    'client_summary': {},
                    'total_projects': 0,
                    'total_clients': 0,
                    'error': 'No CRP/Caribou projects found'
                }
            
            # Analyze by client
            print("Step 2: Analyzing projects by client...")
            client_engagement = {}
            
            for project in crp_projects:
                client_name = project.get('Client_Name', 'Unknown Client')
                
                # Skip if no client name
                if not client_name or client_name == 'Unknown Client':
                    continue
                
                # Initialize client data if not exists
                if client_name not in client_engagement:
                    client_engagement[client_name] = {
                        'total_projects': 0,
                        'projects': [],
                        'project_statuses': {}
                    }
                
                client_data = client_engagement[client_name]
                client_data['total_projects'] += 1
                
                # Add project details
                project_status = project.get('Project_Status', 'Unknown')
                project_name = project.get('Project_Name', 'Unknown Project')
                project_number = project.get('Project_Number', 'N/A')
                
                client_data['projects'].append({
                    'name': project_name,
                    'number': project_number,
                    'status': project_status,
                    'project_id': project.get('Project_ID', 'N/A')
                })
                
                # Track project statuses
                if project_status not in client_data['project_statuses']:
                    client_data['project_statuses'][project_status] = 0
                client_data['project_statuses'][project_status] += 1
            
            print(f"Step 3: Client analysis complete!")
            print(f"  - {len(crp_projects)} CRP/Caribou projects found")
            print(f"  - {len(client_engagement)} clients found")
            
            return {
                'client_summary': client_engagement,
                'total_projects': len(crp_projects),
                'total_clients': len(client_engagement),
                'error': None
            }
            
        except Exception as e:
            print(f"Error analyzing client engagement data: {e}")
            import traceback
            traceback.print_exc()
            return {
                'client_summary': {},
                'total_projects': 0,
                'total_clients': 0,
                'error': str(e)
            }
    
    def get_top_clients(self, client_data: Dict, top_n: int = 10) -> List[Tuple[str, Dict]]:
        """Get the top N clients by project count"""
        clients = [(name, data) for name, data in client_data.items()]
        clients.sort(key=lambda x: x[1]['total_projects'], reverse=True)
        return clients[:top_n]


def main():
    """Test the team engagement analyzer"""
    print("🚀 Testing Team Engagement Analyzer...")
    
    analyzer = TeamEngagementAnalyzer()
    
    # Validate configuration
    config = analyzer.validate_configuration()
    if not config['is_valid']:
        print(f"❌ Configuration incomplete. Missing: {', '.join(config['missing_vars'])}")
        return
    
    if not config['client_available']:
        print("❌ ArcGIS client not available")
        return
    
    print("✅ Configuration valid, running analysis...")
    
    # Run analysis
    result = analyzer.analyze_engagement_data()
    
    if result['error']:
        print(f"❌ Analysis failed: {result['error']}")
        return
    
    # Display results
    print(f"\n📊 TEAM ENGAGEMENT ANALYSIS RESULTS")
    print(f"{'='*50}")
    print(f"Total CRP/Caribou Projects: {result['total_projects']}")
    print(f"People Engaged: {result['total_people']}")
    
    if result['total_people'] > 0:
        avg_projects = round(result['total_projects'] / result['total_people'], 1)
        print(f"Average Projects per Person: {avg_projects}")
    
    # Show top engaged people
    engagement_data = result['engagement_summary']
    if engagement_data:
        print(f"\n👥 TOP ENGAGED PEOPLE:")
        top_people = analyzer.get_top_engaged_people(engagement_data, 5)
        
        for i, (person_name, person_data) in enumerate(top_people, 1):
            total_projects = person_data['total_projects']
            roles = ', '.join(person_data['roles'])
            print(f"  {i}. {person_name}: {total_projects} projects ({roles})")
        
        # Show workload distribution
        print(f"\n📈 WORKLOAD DISTRIBUTION:")
        workload = analyzer.get_workload_distribution(engagement_data)
        for category, count in workload.items():
            print(f"  {category}: {count} people")
        
        # Show role distribution
        print(f"\n🎭 ROLE DISTRIBUTION:")
        roles = analyzer.get_role_distribution(engagement_data)
        for role, count in roles.items():
            role_label = f"{role} Only" if role != 'Both' else 'Both Roles'
            print(f"  {role_label}: {count} people")
    
    print(f"\n✅ Analysis complete!")


if __name__ == "__main__":
    main()
