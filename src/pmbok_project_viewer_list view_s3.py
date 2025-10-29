#!/usr/bin/env python3
"""
PMBOK-Aligned Project Management Dashboard for Caribou Portal
Implements PMI PMBOK 7th Edition standards with 10 Knowledge Areas and 5 Process Groups
"""

import json
import os
import sys
import glob
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from nicegui import ui
import requests
from dotenv import load_dotenv
import boto3 

# Optional imports
try:
    import yaml
except ImportError:
    yaml = None
    print("PyYAML not installed, Dendron integration features will be limited")

load_dotenv()
#s3 env variables
AWS_ACCESS_KEY_ID = os.environ["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = os.environ["AWS_SECRET_ACCESS_KEY"]
AWS_S3_ENDPOINT = os.environ["AWS_S3_ENDPOINT"]
AWS_S3_BUCKET = os.environ["AWS_S3_BUCKET"]
STATUS_PATH= os.environ["STATUS_PATH"]
PROJECTS_PATH= os.environ["PROJECTS_PATH"]

s3_client = boto3.client(
    "s3",
    endpoint_url=AWS_S3_ENDPOINT,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)
bucket = AWS_S3_BUCKET

class PMBOKProjectViewer:
    """PMI PMBOK-aligned project management viewer"""
    
    def __init__(self):
        # self.json_file_path = json_file_path
        # self.status_overrides_file = '/home/cfolkers/caribou_portal/project_status_overrides.json'
        self.projects = self.load_projects()
        self.status_overrides = self.load_status_overrides()
        
        # PMBOK Process Groups
        self.process_groups = {
            'initiating': 'Initiating',
            'planning': 'Planning', 
            'executing': 'Executing',
            'monitoring': 'Monitoring & Controlling',
            'closing': 'Closing'
        }
        
        # Enhanced Project Status Categories
        self.project_status_categories = {
            'not_assigned': {
                'name': 'Not Assigned',
                'description': 'Projects without assigned team members or lead',
                'color': 'red',
                'icon': 'person_off',
                'statuses': ['Not Assigned', 'Unassigned', 'Pending Assignment']
            },
            'not_started': {
                'name': 'Not Started',
                'description': 'Projects assigned but work not yet begun',
                'color': 'gray',
                'icon': 'schedule',
                'statuses': ['Assigned', 'New', 'Queued']
            },
            'in_progress': {
                'name': 'In Progress',
                'description': 'Active project work underway',
                'color': 'blue',
                'icon': 'play_arrow',
                'statuses': ['In Progress', 'Active', 'Working']
            },
            'awaiting_client': {
                'name': 'Awaiting Client Feedback',
                'description': 'Waiting for client input or approval',
                'color': 'yellow',
                'icon': 'feedback',
                'statuses': ['Awaiting Client Feedback', 'Client Review', 'Pending Client']
            },
            'awaiting_resources': {
                'name': 'Awaiting Resources',
                'description': 'Blocked waiting for team members or tools',
                'color': 'orange',
                'icon': 'people',
                'statuses': ['Awaiting Resources', 'Resource Blocked', 'Team Unavailable']
            },
            'on_hold': {
                'name': 'On Hold',
                'description': 'Temporarily paused projects',
                'color': 'red',
                'icon': 'pause',
                'statuses': ['On Hold', 'Paused', 'Suspended']
            },
            'quality_review': {
                'name': 'Quality Review',
                'description': 'Under quality assurance or technical review',
                'color': 'purple',
                'icon': 'fact_check',
                'statuses': ['Quality Review', 'QA Review', 'Technical Review']
            },
            'completed': {
                'name': 'Completed',
                'description': 'Successfully completed projects',
                'color': 'green',
                'icon': 'check_circle',
                'statuses': ['Completed', 'Done', 'Finished', 'Delivered']
            },
            'cancelled': {
                'name': 'Cancelled',
                'description': 'Cancelled or terminated projects',
                'color': 'gray',
                'icon': 'cancel',
                'statuses': ['Cancelled', 'Terminated', 'Discontinued']
            }
        }
        
        # PMBOK Knowledge Areas
        self.knowledge_areas = {
            'integration': 'Project Integration Management',
            'scope': 'Project Scope Management',
            'schedule': 'Project Schedule Management',
            'cost': 'Project Cost Management',
            'quality': 'Project Quality Management',
            'resource': 'Project Resource Management',
            'communications': 'Project Communications Management',
            'risk': 'Project Risk Management',
            'procurement': 'Project Procurement Management',
            'stakeholder': 'Project Stakeholder Management'
        }
    
    def load_projects(self) -> List[Dict[str, Any]]:
        """Load projects from JSON file"""
        # if not os.path.exists(self.json_file_path):
        #     return []
        resp = s3_client.get_object(Bucket=bucket, Key=PROJECTS_PATH)
        body_bytes = resp['Body'].read()
        try:
            return json.loads(body_bytes.decode('utf-8'))
        except Exception as e:
            print(f"Error loading JSON file: {e}")
            return []
    
    def refresh_data(self):
        """Refresh project data from file"""
        self.projects = self.load_projects()
        self.status_overrides = self.load_status_overrides()
        return len(self.projects)
    
    def load_status_overrides(self):
        """Load local status overrides from JSON file"""
        
        # try:
        #     with open(self.status_overrides_file, 'r') as f:
        #         return json.load(f)
        # except FileNotFoundError:
        #     # Create empty overrides file if it doesn't exist
        #     return {}
        # except json.JSONDecodeError:
        #     print(f"Error: Invalid JSON in {self.status_overrides_file}")
        #     return {}
        resp = s3_client.get_object(Bucket=bucket, Key=STATUS_PATH)
        body_bytes = resp['Body'].read()
        try:
            return json.loads(body_bytes.decode('utf-8'))
        except Exception as e:
            print(f"Error loading JSON file: {e}")
            return []
        
    
    def save_status_overrides(self):
        """Save status overrides to JSON file"""
        # try:
        #     with open(self.status_overrides_file, 'w') as f:
        #         json.dump(self.status_overrides, f, indent=2)
        #     return True
        # except Exception as e:
        #     print(f"Error saving status overrides: {e}")
        #     return False
        try:
            # Convert the overrides dict to JSON bytes
            json_bytes = json.dumps(self.status_overrides, indent=2).encode('utf-8')
            # Put object to S3
            s3_client.put_object(Bucket=bucket, Key=STATUS_PATH, Body=json_bytes, ContentType='application/json')
            return True
        except Exception as e:
            print(f"Error saving status overrides to S3: {e}")
            return False
    
    def get_project_effective_status(self, project):
        """Get the effective status for a project (override or original)"""
        project_id = project.get('Project_ID', '')
        if str(project_id) in self.status_overrides:
            return self.status_overrides[str(project_id)]['status']
        return project.get('Project_Status', 'Unknown')
    
    def update_project_status(self, project_id: str, new_status: str, updated_by: str = 'User'):
        """Update a project's status locally"""
        from datetime import datetime
        if str(project_id) not in self.status_overrides:
            self.status_overrides[str(project_id)] = {}
        
        self.status_overrides[str(project_id)].update({
            'status': new_status,
            'updated_by': updated_by,
            'updated_at': datetime.now().isoformat(),
            'original_status': next((p.get('Project_Status', 'Unknown') for p in self.projects if str(p.get('Project_ID', '')) == str(project_id)), 'Unknown')
        })
        return self.save_status_overrides()
    
    def update_project_notes(self, project_id: str, notes: str, updated_by: str = 'User'):
        """Update a project's notes locally"""
        from datetime import datetime
        if str(project_id) not in self.status_overrides:
            self.status_overrides[str(project_id)] = {}
        
        self.status_overrides[str(project_id)].update({
            'notes': notes,
            'notes_updated_by': updated_by,
            'notes_updated_at': datetime.now().isoformat()
        })
        return self.save_status_overrides()
    
    def get_project_notes(self, project_id: str) -> str:
        """Get notes for a project"""
        if str(project_id) in self.status_overrides:
            return self.status_overrides[str(project_id)].get('notes', '')
        return ''
    
    def update_coordinator_actions(self, project_id: str, actions: str, updated_by: str = 'User'):
        """Update a project's coordinator actions locally"""
        from datetime import datetime
        if str(project_id) not in self.status_overrides:
            self.status_overrides[str(project_id)] = {}
        
        self.status_overrides[str(project_id)].update({
            'coordinator_actions': actions,
            'coordinator_actions_updated_by': updated_by,
            'coordinator_actions_updated_at': datetime.now().isoformat()
        })
        return self.save_status_overrides()
    
    def get_coordinator_actions(self, project_id: str) -> str:
        """Get coordinator actions for a project"""
        if str(project_id) in self.status_overrides:
            return self.status_overrides[str(project_id)].get('coordinator_actions', '')
        return ''
    
    def format_actions_as_bullets(self, actions_text: str) -> str:
        """Format actions text as bulleted list for display"""
        if not actions_text:
            return ''
        
        # Split by lines and add bullets
        lines = [line.strip() for line in actions_text.split('\n') if line.strip()]
        return '\n'.join([f'• {line}' if not line.startswith('•') else line for line in lines])
    
    def parse_actions_from_bullets(self, bulleted_text: str) -> str:
        """Parse bulleted text back to plain text for editing"""
        if not bulleted_text:
            return ''
        
        # Remove bullets for editing
        lines = [line.strip() for line in bulleted_text.split('\n') if line.strip()]
        return '\n'.join([line[2:] if line.startswith('• ') else line for line in lines])
    
    def calculate_days_until_due(self, project):
        """Calculate days until project due date"""
        from datetime import datetime
        due_date_str = project.get('Date_Required', '') or project.get('Required_Date', '')
        
        if not due_date_str or due_date_str == 'None':
            return None
        
        try:
            # Handle epoch milliseconds (ArcGIS format)
            if isinstance(due_date_str, (int, float)):
                # Convert milliseconds to seconds and create datetime
                due_date = datetime.fromtimestamp(due_date_str / 1000)
            else:
                # Try multiple date formats for string dates
                date_formats = [
                    '%Y-%m-%d',
                    '%m/%d/%Y', 
                    '%Y-%m-%d %H:%M:%S',
                    '%Y-%m-%dT%H:%M:%S',
                    '%Y-%m-%dT%H:%M:%S.%f'
                ]
                
                due_date = None
                for fmt in date_formats:
                    try:
                        due_date = datetime.strptime(str(due_date_str).split('T')[0].split(' ')[0], fmt.split(' ')[0])
                        break
                    except ValueError:
                        continue
                
                if due_date is None:
                    return None
            
            today = datetime.now()
            delta = (due_date - today).days
            return delta
            
        except Exception as e:
            print(f"Error parsing date {due_date_str}: {e}")
            return None
    
    def get_team_members_list(self, project):
        """Get formatted list of team members"""
        team_members = []
        
        # Add project lead/coordinator
        lead = project.get('Project_Team_Lead', '') or project.get('Team_Member', '') or 'Cole Folkers'
        if lead and lead != 'N/A' and isinstance(lead, str):
            team_members.append(f"{lead} (Lead)")
        
        # Add other team members if available
        other_members = project.get('Team_Members', [])
        if isinstance(other_members, list):
            for member in other_members:
                # Only add string members, skip dict objects
                if isinstance(member, str) and member.strip():
                    team_members.append(member.strip())
        elif isinstance(other_members, str) and other_members:
            # Handle comma-separated string
            members = [m.strip() for m in other_members.split(',') if m.strip()]
            team_members.extend(members)
        
        # Remove duplicates while preserving order (only for strings)
        seen = set()
        unique_members = []
        for member in team_members:
            if isinstance(member, str) and member not in seen:
                seen.add(member)
                unique_members.append(member)
        
        return unique_members if unique_members else ['Cole Folkers (Lead)']
    
    def get_due_date_status(self, days_until_due):
        """Get status and color for due date"""
        if days_until_due is None:
            return 'No due date', 'gray'
        elif days_until_due < 0:
            return f'{abs(days_until_due)} days overdue', 'red'
        elif days_until_due == 0:
            return 'Due today', 'red'
        elif days_until_due <= 7:
            return f'{days_until_due} days left', 'yellow'
        elif days_until_due <= 30:
            return f'{days_until_due} days left', 'blue'
        else:
            return f'{days_until_due} days left', 'green'
    
    def sort_projects_by_due_date(self, projects):
        """Sort projects by due date (nearest/overdue first)"""
        def get_sort_key(project):
            days_until_due = self.calculate_days_until_due(project)
            if days_until_due is None:
                return float('inf')  # Projects without due dates go to the end
            return days_until_due
        
        return sorted(projects, key=get_sort_key)
        return len(self.projects)
    
    def get_project_by_id(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific project by ID"""
        for project in self.projects:
            if project.get('Project_ID') == project_id:
                return project
        return None
    
    def format_date(self, timestamp: int) -> str:
        """Convert timestamp to readable date"""
        if not timestamp:
            return "N/A"
        try:
            return datetime.fromtimestamp(timestamp / 1000).strftime("%Y-%m-%d")
        except:
            return "Invalid Date"
    
    def get_project_phase(self, project: Dict[str, Any]) -> str:
        """Determine PMBOK Process Group based on project status and dates"""
        status = project.get('Project_Status', '').lower()
        date_requested = project.get('Date_Requested', 0)
        date_required = project.get('Date_Required', 0)
        
        if status == 'assigned':
            # Check if recently assigned (within 2 weeks) - likely still initiating/planning
            if date_requested:
                request_date = datetime.fromtimestamp(date_requested / 1000)
                if (datetime.now() - request_date).days <= 14:
                    return 'initiating'
                else:
                    return 'executing'
            return 'planning'
        elif status == 'in progress':
            return 'executing'
        elif status == 'completed':
            return 'closing'
        elif status == 'on hold':
            return 'monitoring'
        else:
            return 'initiating'
    
    def calculate_schedule_performance(self, project: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate Schedule Performance Index (SPI) and variance"""
        date_requested = project.get('Date_Requested', 0)
        date_required = project.get('Date_Required', 0)
        
        if not date_requested or not date_required:
            return {
                'status': 'Unknown',
                'variance_days': 0,
                'health': 'gray',
                'spi': 'N/A'
            }
        
        start_date = datetime.fromtimestamp(date_requested / 1000)
        end_date = datetime.fromtimestamp(date_required / 1000)
        current_date = datetime.now()
        
        total_duration = (end_date - start_date).days
        elapsed_duration = (current_date - start_date).days
        remaining_duration = (end_date - current_date).days
        
        # Simple SPI calculation (planned vs actual progress)
        if total_duration > 0:
            planned_progress = elapsed_duration / total_duration
            # Assume linear progress for simplicity
            actual_progress = min(planned_progress, 1.0)
            spi = actual_progress / planned_progress if planned_progress > 0 else 1.0
        else:
            spi = 1.0
        
        # Schedule health
        if remaining_duration < 0:
            health = 'red'
            status = 'Overdue'
        elif remaining_duration <= 7:
            health = 'yellow'
            status = 'At Risk'
        elif spi < 0.9:
            health = 'yellow'
            status = 'Behind Schedule'
        else:
            health = 'green'
            status = 'On Track'
        
        return {
            'status': status,
            'variance_days': remaining_duration,
            'health': health,
            'spi': round(spi, 2) if isinstance(spi, float) else spi,
            'total_duration': total_duration,
            'elapsed_duration': elapsed_duration,
            'remaining_duration': remaining_duration
        }
    
    def get_risk_level(self, project: Dict[str, Any]) -> Dict[str, str]:
        """Assess project risk level based on PMBOK risk management"""
        schedule_perf = self.calculate_schedule_performance(project)
        priority = project.get('Priority_Level', 'Normal').lower()
        
        risk_factors = 0
        
        # Schedule risk
        if schedule_perf['health'] == 'red':
            risk_factors += 3
        elif schedule_perf['health'] == 'yellow':
            risk_factors += 2
        
        # Priority risk
        if priority == 'urgent':
            risk_factors += 2
        elif priority == 'high':
            risk_factors += 1
        
        # Team size risk (larger teams = more complexity)
        team_size = len(project.get('Team_Members', [])) + 1  # +1 for coordinator
        if team_size == 1:
            risk_factors += 1  # Single person risk
        elif team_size > 4:
            risk_factors += 1  # Large team coordination risk
        
        # Determine overall risk
        if risk_factors >= 5:
            return {'level': 'High', 'color': 'red', 'score': risk_factors}
        elif risk_factors >= 3:
            return {'level': 'Medium', 'color': 'yellow', 'score': risk_factors}
        else:
            return {'level': 'Low', 'color': 'green', 'score': risk_factors}
    
    def get_stakeholder_analysis(self, project: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze project stakeholders per PMBOK stakeholder management"""
        stakeholders = {
            'primary': [],
            'secondary': [],
            'internal': [],
            'external': []
        }
        
        # Primary stakeholders
        client_name = project.get('Client_Name')
        if client_name:
            stakeholders['primary'].append({
                'name': client_name,
                'role': 'Project Sponsor/Client',
                'influence': 'High',
                'interest': 'High'
            })
        
        stakeholders['primary'].append({
            'name': 'Cole Folkers',
            'role': 'Project Manager/Coordinator',
            'influence': 'High',
            'interest': 'High'
        })
        
        # Team members
        for member in project.get('Team_Members', []):
            stakeholders['primary'].append({
                'name': member.get('Resource_Name', 'Unknown'),
                'role': 'Team Member',
                'influence': 'Medium',
                'interest': 'High'
            })
        
        # Secondary stakeholders
        ministry = project.get('Ministry')
        if ministry:
            stakeholders['secondary'].append({
                'name': ministry,
                'role': 'Ministry/Department',
                'influence': 'Medium',
                'interest': 'Medium'
            })
        
        # Classify internal vs external
        for category in ['primary', 'secondary']:
            for stakeholder in stakeholders[category]:
                if 'gov.bc.ca' in project.get('Client_Email', '') or 'Ministry' in stakeholder.get('role', ''):
                    stakeholders['internal'].append(stakeholder)
                else:
                    stakeholders['external'].append(stakeholder)
        
        return stakeholders
    
    def get_project_status_category(self, project):
        """Determine which status category a project belongs to"""
        project_status = self.get_project_effective_status(project).strip()
        
        if not project_status:
            return 'not_started'
            
        # Check each category for matching status
        for category_key, category_info in self.project_status_categories.items():
            if project_status in category_info['statuses']:
                return category_key
                
        # If status doesn't match predefined categories, try to infer
        status_lower = project_status.lower()
        
        if any(word in status_lower for word in ['progress', 'active', 'working']):
            return 'in_progress'
        elif any(word in status_lower for word in ['client', 'feedback', 'review']):
            return 'awaiting_client'
        elif any(word in status_lower for word in ['hold', 'pause', 'suspend']):
            return 'on_hold'
        elif any(word in status_lower for word in ['complete', 'done', 'finish']):
            return 'completed'
        elif any(word in status_lower for word in ['cancel', 'terminate']):
            return 'cancelled'
        else:
            return 'not_started'  # Default category
    
    def get_projects_by_status_category(self, category_key):
        """Get all projects in a specific status category"""
        return [p for p in self.projects if self.get_project_status_category(p) == category_key]
    
    def get_status_category_summary(self):
        """Get count of projects in each status category"""
        summary = {}
        for category_key, category_info in self.project_status_categories.items():
            projects = self.get_projects_by_status_category(category_key)
            summary[category_key] = {
                'count': len(projects),
                'info': category_info,
                'projects': projects
            }
        return summary
    
    def get_status_color(self, status: str) -> str:
        """Get color class for project status based on category"""
        category = self.get_project_status_category({'Project_Status': status})
        category_info = self.project_status_categories[category]
        
        color_map = {
            'slate': 'bg-slate-500',
            'gray': 'bg-gray-500',
            'blue': 'bg-blue-500', 
            'yellow': 'bg-yellow-500',
            'orange': 'bg-orange-500',
            'red': 'bg-red-500',
            'purple': 'bg-purple-500',
            'green': 'bg-green-500'
        }
        
        return color_map.get(category_info['color'], 'bg-gray-500')
    
    def get_project_metrics(self) -> Dict[str, Any]:
        """Calculate portfolio-level metrics per PMBOK"""
        if not self.projects:
            return {}
        
        total = len(self.projects)
        
        # Process Group distribution
        process_distribution = {group: 0 for group in self.process_groups.keys()}
        risk_distribution = {'Low': 0, 'Medium': 0, 'High': 0}
        schedule_health = {'green': 0, 'yellow': 0, 'red': 0}
        
        overdue_count = 0
        at_risk_count = 0
        
        for project in self.projects:
            # Process group
            phase = self.get_project_phase(project)
            process_distribution[phase] += 1
            
            # Risk analysis
            risk = self.get_risk_level(project)
            risk_distribution[risk['level']] += 1
            
            # Schedule health
            schedule_perf = self.calculate_schedule_performance(project)
            schedule_health[schedule_perf['health']] += 1
            
            if schedule_perf['variance_days'] < 0:
                overdue_count += 1
            elif schedule_perf['variance_days'] <= 7:
                at_risk_count += 1
        
        return {
            'total_projects': total,
            'process_distribution': process_distribution,
            'risk_distribution': risk_distribution,
            'schedule_health': schedule_health,
            'overdue_count': overdue_count,
            'at_risk_count': at_risk_count,
            'on_track_count': total - overdue_count - at_risk_count
        }
    
    def get_dendron_vault_path(self):
        """Get the user's Dendron vault path from DENDRON environment variable or common locations"""
        import os
        from pathlib import Path
        
        # First check DENDRON environment variable
        dendron_env_path = os.getenv('DENDRON')
        if dendron_env_path:
            expanded_path = os.path.expanduser(dendron_env_path)
            if os.path.exists(expanded_path):
                dendron_config = os.path.join(expanded_path, "dendron.yml")
                if os.path.exists(dendron_config):
                    return expanded_path
                else:
                    print(f"⚠️ DENDRON path exists but no dendron.yml found: {expanded_path}")
            else:
                print(f"⚠️ DENDRON environment variable path does not exist: {expanded_path}")
        
        # Fallback to common Dendron vault locations
        potential_paths = [
            os.path.expanduser("~/Dendron"),
            os.path.expanduser("~/dendron"),
            os.path.expanduser("~/Documents/Dendron"),
            os.path.expanduser("~/Documents/dendron"),
            os.path.expanduser("~/notes"),
            os.path.expanduser("~/Notes"),
            # VS Code workspace folders
            os.path.expanduser("~/.vscode/workspaces"),
        ]
        
        # Check for dendron.yml file to confirm vault
        for path in potential_paths:
            if os.path.exists(path):
                dendron_config = os.path.join(path, "dendron.yml")
                if os.path.exists(dendron_config):
                    return path
                    
                # Also check subdirectories for vaults
                try:
                    for item in os.listdir(path):
                        subpath = os.path.join(path, item)
                        if os.path.isdir(subpath):
                            subdendron_config = os.path.join(subpath, "dendron.yml")
                            if os.path.exists(subdendron_config):
                                return subpath
                except PermissionError:
                    continue
        
        return None
    
    def find_project_notes_in_dendron(self, project_id: str, vault_path: str = None):
        """Find notes related to a specific project in Dendron vault using WLRS.LUP.CRP hierarchy"""
        if not vault_path:
            vault_path = self.get_dendron_vault_path()
            if not vault_path:
                return []
        
        import os
        import glob
        
        project_notes = []
        
        # Search patterns for project-related notes using the new hierarchy
        search_patterns = [
            f"WLRS.LUP.CRP.caribou-portal.{project_id}*",
            f"*{project_id}*",  # Fallback for any existing notes
        ]
        
        try:
            # Get project name for additional search
            project = self.get_project_by_id(project_id)
            if project and project.get('Project_Name'):
                project_name = project['Project_Name'].lower().replace(' ', '-')
                search_patterns.extend([
                    f"WLRS.LUP.CRP.caribou-portal.{project_name}*",
                ])
            
            # Search for markdown files
            for pattern in search_patterns:
                md_files = glob.glob(os.path.join(vault_path, f"{pattern}.md"), recursive=False)
                for file_path in md_files:
                    if os.path.isfile(file_path):
                        rel_path = os.path.relpath(file_path, vault_path)
                        project_notes.append({
                            'path': file_path,
                            'relative_path': rel_path,
                            'name': os.path.basename(file_path),
                            'modified': os.path.getmtime(file_path)
                        })
        
        except Exception as e:
            print(f"Error searching Dendron vault: {e}")
            return []
        
        # Remove duplicates and sort by modification time
        unique_notes = {note['path']: note for note in project_notes}.values()
        return sorted(unique_notes, key=lambda x: x['modified'], reverse=True)
    
    def create_main_caribou_portal_note(self, vault_path: str = None):
        """Create the main WLRS.LUP.CRP.caribou-portal note with links to all project notes"""
        if not vault_path:
            vault_path = self.get_dendron_vault_path()
            if not vault_path:
                return None
        
        import os
        from datetime import datetime
        import yaml
        
        try:
            # Main note filename
            note_filename = "WLRS.LUP.CRP.caribou-portal.md"
            note_path = os.path.join(vault_path, note_filename)
            
            # Create note content with frontmatter
            now = datetime.now()
            frontmatter = {
                'id': 'wlrs.lup.crp.caribou-portal',
                'title': 'Caribou Portal - PMBOK Project Management System',
                'desc': 'Main hub for PMBOK-aligned project management in Dendron',
                'updated': int(now.timestamp()),
                'created': int(now.timestamp()),
                'tags': ['caribou-portal', 'pmbok', 'project-management', 'index'],
                'children': []
            }
            
            # Get all active projects
            active_projects = [p for p in self.projects if p.get('Status', '').lower() in ['active', 'in progress']]
            metrics = self.get_project_metrics()
            
            # Add children references
            for project in active_projects:
                project_id = project.get('Project_ID', '')
                if project_id:
                    frontmatter['children'].append(f'wlrs.lup.crp.caribou-portal.{project_id}')
            
            content = f"""---
{yaml.dump(frontmatter, default_flow_style=False).strip() if yaml else '# YAML frontmatter unavailable'}
---

# Caribou Portal - PMBOK Project Management System

> **PMBOK 7th Edition Aligned Dashboard**  
> PMI Project Management Body of Knowledge implementation for portfolio management

## 🚀 Quick Access
- 🌐 [Portfolio Dashboard](http://localhost:8080)
- 📊 [PMBOK Analysis Report](http://localhost:8080/pmbok-report)
- 📋 [Status Dashboard](http://localhost:8080/status-dashboard)
- � [GSS Caribou Support Information](http://localhost:8080/dendron-integration)

## 📊 Portfolio Metrics
- **Total Projects**: {metrics.get('total_projects', 0)}
- **On Track**: {metrics.get('on_track_count', 0)}
- **At Risk**: {metrics.get('at_risk_count', 0)}
- **Overdue**: {metrics.get('overdue_count', 0)}

---

## 🎯 Active Projects

{chr(10).join([f"### [[WLRS.LUP.CRP.caribou-portal.{p.get('Project_ID', '')}|{p.get('Project_ID', '')}: {p.get('Project_Name', 'Unnamed Project')}]]" + chr(10) + f"- **Status**: {p.get('Status', 'Unknown')}" + chr(10) + f"- **Lead**: {p.get('Project_Team_Lead', 'Unassigned')}" + chr(10) + f"- **Due**: {p.get('Required_Date', 'Not specified')}" + chr(10) for p in active_projects[:10]])}

{f'*...and {len(active_projects) - 10} more projects*' if len(active_projects) > 10 else ''}

---

## 📚 PMBOK Knowledge Areas

### Integration Management
- Project charter and management plans
- Change control and project closure

### Scope Management  
- Requirements gathering and WBS
- Scope verification and control

### Schedule Management
- Activity definition and sequencing
- Duration estimation and schedule control

### Cost Management
- Cost estimation and budgeting
- Cost control and earned value

### Quality Management
- Quality planning and assurance
- Quality control and improvement

### Resource Management
- Team development and management
- Resource allocation and optimization

### Communications Management
- Communication planning and distribution
- Stakeholder reporting and feedback

### Risk Management
- Risk identification and analysis
- Risk response and monitoring

### Procurement Management
- Procurement planning and execution
- Contract administration and closure

### Stakeholder Management
- Stakeholder identification and engagement
- Stakeholder communication and satisfaction

---

## 📝 Note Templates

Create standardized project notes:
- **Project Overview**: [[WLRS.LUP.CRP.caribou-portal.PROJECT_ID]]
- **Meeting Notes**: [[WLRS.LUP.CRP.caribou-portal.PROJECT_ID.meetings]]
- **Task Tracking**: [[WLRS.LUP.CRP.caribou-portal.PROJECT_ID.tasks]]
- **Decision Log**: [[WLRS.LUP.CRP.caribou-portal.PROJECT_ID.decisions]]
- **Risk Register**: [[WLRS.LUP.CRP.caribou-portal.PROJECT_ID.risks]]

---

## 🔄 Recent Updates
*Last updated: {now.strftime("%Y-%m-%d %H:%M:%S")}*

---

## Related Systems
- [[WLRS.LUP.CRP]] - Collaborative Resource Platform
- Project management workflows
- Team collaboration standards
"""
            
            # Write the note file
            with open(note_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return note_path
        
        except Exception as e:
            print(f"Error creating main Caribou Portal note: {e}")
            return None
    
    def read_dendron_note(self, note_path: str):
        """Read content from a Dendron note file"""
        try:
            with open(note_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse frontmatter if it exists
            frontmatter = {}
            content_body = content
            
            if content.startswith('---\n'):
                try:
                    end_index = content.find('\n---\n', 4)
                    if end_index != -1:
                        import yaml
                        frontmatter_text = content[4:end_index]
                        frontmatter = yaml.safe_load(frontmatter_text) or {}
                        content_body = content[end_index + 5:]
                except Exception as e:
                    print(f"Error parsing frontmatter: {e}")
            
            return {
                'content': content_body.strip(),
                'frontmatter': frontmatter,
                'full_content': content
            }
        
        except Exception as e:
            print(f"Error reading Dendron note {note_path}: {e}")
            return None
    
    def create_dendron_project_note(self, project_id: str, vault_path: str = None):
        """Create a new Dendron note for a project using WLRS.LUP.CRP.caribou-portal hierarchy"""
        if not vault_path:
            vault_path = self.get_dendron_vault_path()
            if not vault_path:
                return None
        
        import os
        from datetime import datetime
        import yaml
        
        try:
            project = self.get_project_by_id(project_id)
            if not project:
                return None
            
            project_name = project.get('Project_Name', f'Project {project_id}')
            safe_project_name = project_name.lower().replace(' ', '-').replace('/', '-')
            
            # Use hierarchical structure: WLRS.LUP.CRP.caribou-portal.{project-id}
            note_filename = f"WLRS.LUP.CRP.caribou-portal.{project_id}.md"
            note_path = os.path.join(vault_path, note_filename)
            
            # Check if note already exists
            if os.path.exists(note_path):
                return note_path
            
            # Create note content with frontmatter
            now = datetime.now()
            frontmatter = {
                'id': f'wlrs.lup.crp.caribou-portal.{project_id}',
                'title': f'Caribou Portal - Project {project_id}: {project_name}',
                'desc': f'PMBOK project management for {project_name} (ID: {project_id})',
                'updated': int(now.timestamp()),
                'created': int(now.timestamp()),
                'project_id': project_id,
                'project_name': project_name,
                'status': project.get('Status', 'Active'),
                'tags': ['caribou-portal', 'pmbok', 'project', project_id.lower()],
                'parent': 'WLRS.LUP.CRP.caribou-portal'
            }
            
            # Get additional project details
            team_members = self.get_team_members_list(project)
            due_date = project.get('Required_Date', 'Not specified')
            team_lead = project.get('Project_Team_Lead', 'Unassigned')
            
            content = f"""---
{yaml.dump(frontmatter, default_flow_style=False).strip() if yaml else '# YAML frontmatter unavailable'}
---

# Caribou Portal - Project {project_id}: {project_name}

> Part of the [[WLRS.LUP.CRP.caribou-portal]] PMBOK project management system

## Quick Links
- 🌐 [PMBOK Portal Project View](http://localhost:8080/pmbok/{project_id})
- 📊 [Project Dashboard](http://localhost:8080)
- � [GSS Caribou Support Information](http://localhost:8080/dendron-integration)

## Project Overview
- **Project ID**: {project_id}
- **Status**: {project.get('Status', 'Active')}
- **Team Lead**: {team_lead}
- **Due Date**: {due_date}
- **PMBOK Phase**: {self.get_project_phase(project)}

## Team Members
{chr(10).join([f'- {member}' for member in team_members]) if team_members else '- No team members assigned'}

## Project Details
- **Description**: {project.get('Description', 'No description available')}
- **Priority**: {project.get('Priority', 'Not specified')}
- **Project Number**: {project.get('Project_Number', 'Not specified')}

---

## 📝 Project Notes

### Meeting Notes
<!-- Add meeting notes here -->

### Action Items
<!-- Add action items here -->
- [ ] 

### Decisions Made
<!-- Add project decisions here -->

### Risks & Issues
<!-- Add risks and issues here -->

---

## Related Pages
<!-- Links to related Dendron notes -->
- [[WLRS.LUP.CRP.caribou-portal.{project_id}.meetings]] - Meeting notes
- [[WLRS.LUP.CRP.caribou-portal.{project_id}.tasks]] - Task tracking
- [[WLRS.LUP.CRP.caribou-portal.{project_id}.decisions]] - Decision log
- [[WLRS.LUP.CRP.caribou-portal.{project_id}.risks]] - Risk register

---

## PMBOK Knowledge Areas
<!-- Reference to PMBOK framework -->
- **Integration Management**: Overall project coordination
- **Scope Management**: Project deliverables and requirements
- **Schedule Management**: Timeline and milestone tracking
- **Cost Management**: Budget and resource allocation
- **Quality Management**: Quality standards and assurance
- **Resource Management**: Team and material resources
- **Communications Management**: Stakeholder communication
- **Risk Management**: Risk identification and mitigation
- **Procurement Management**: External vendor management
- **Stakeholder Management**: Stakeholder engagement

---

*Generated by Caribou Portal PMBOK System on {now.strftime("%Y-%m-%d %H:%M:%S")}*
"""
            
            # Write the note file
            with open(note_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return note_path
        
        except Exception as e:
            print(f"Error creating Dendron note: {e}")
            return None
    
    def get_dendron_integration_status(self):
        """Check Dendron integration status and capabilities"""
        vault_path = self.get_dendron_vault_path()
        
        status = {
            'vault_found': vault_path is not None,
            'vault_path': vault_path,
            'can_read': False,
            'can_write': False,
            'note_count': 0,
            'project_notes': 0
        }
        
        if vault_path:
            import os
            
            # Check read permissions
            try:
                status['can_read'] = os.access(vault_path, os.R_OK)
            except:
                pass
            
            # Check write permissions
            try:
                status['can_write'] = os.access(vault_path, os.W_OK)
            except:
                pass
            
            # Count notes
            try:
                import glob
                all_notes = glob.glob(os.path.join(vault_path, "**", "*.md"), recursive=True)
                status['note_count'] = len(all_notes)
                
                # Count project-related notes
                project_notes = [n for n in all_notes if 'project' in os.path.basename(n).lower()]
                status['project_notes'] = len(project_notes)
            except:
                pass
        
        return status

    # def get_team_engagement_analyzer(self):
    #     """Get team engagement analyzer instance"""
    #     try:
    #         from enhanced_get_team_engagement import TeamEngagementAnalyzer
    #         return TeamEngagementAnalyzer()
    #     except Exception as e:
    #         print(f"Error loading team engagement analyzer: {e}")
    #         return None

    # def analyze_engagement_data(self):
    #     """Analyze engagement data using the dedicated team engagement module"""
    #     try:
    #         analyzer = self.get_team_engagement_analyzer()
    #         if not analyzer:
    #             return {
    #                 'engagement_summary': {},
    #                 'total_projects': 0,
    #                 'total_people': 0,
    #                 'error': 'Team engagement analyzer not available'
    #             }
            
    #         return analyzer.analyze_engagement_data()
            
    #     except Exception as e:
    #         print(f"Error in engagement analysis: {e}")
    #         return {
    #             'engagement_summary': {},
    #             'total_projects': 0,
    #             'total_people': 0,
    #             'error': str(e)
    #         }


# Initialize PMBOK-aligned project viewer
# json_file_path = "/home/cfolkers/caribou_portal/projects_for_Cole_Folkers.json"
pmbok_viewer = PMBOKProjectViewer()


@ui.page('/status-dashboard')
def status_dashboard():
    """Project status dashboard organized by lifecycle stage"""
    ui.page_title("Project Status Dashboard")
    
    with ui.row().classes('w-full'):
        # Header
        with ui.card().classes('w-full'):
            ui.label('Project Status Dashboard').classes('text-3xl font-bold text-center')
            ui.label('Organized by Project Lifecycle Stage').classes('text-lg text-center text-gray-600')
    
    # Navigation buttons
    with ui.row().classes('w-full justify-center gap-4 mb-6'):
        ui.button('Portfolio Overview', on_click=lambda: ui.navigate.to('/')).classes('bg-blue-500 text-white')
        ui.button('PMBOK Analysis', on_click=lambda: ui.navigate.to('/pmbok-report')).classes('bg-green-500 text-white')
        # ui.button('Team Engagement', on_click=lambda: ui.navigate.to('/engagement')).classes('bg-purple-500 text-white')
    
    # Get status category summary
    status_summary = pmbok_viewer.get_status_category_summary()
    
    # Create status category grid
    with ui.grid(columns=3).classes('w-full gap-4'):
        for category_key, summary in status_summary.items():
            if summary['count'] > 0:  # Only show categories with projects
                category_info = summary['info']
                
                with ui.card().classes('hover:shadow-lg transition-shadow'):
                    with ui.card_section():
                        # Category header
                        with ui.row().classes('items-center gap-2'):
                            ui.icon(category_info['icon']).classes(f'text-{category_info["color"]}-500 text-2xl')
                            ui.label(category_info['name']).classes('text-xl font-bold')
                        
                        ui.label(category_info['description']).classes('text-gray-600 text-sm mb-2')
                        ui.label(f"{summary['count']} projects").classes(f'text-{category_info["color"]}-600 font-semibold')
                        
                        # View category button
                        ui.button(f'View {category_info["name"]} Projects', 
                                on_click=lambda cat=category_key: ui.navigate.to(f'/status/{cat}')
                        ).classes(f'bg-{category_info["color"]}-500 text-white w-full mt-2')
                        
                        # Quick project list preview (first 3)
                        preview_projects = summary['projects'][:3]
                        for project in preview_projects:
                            project_id = project.get('Project_ID', 'N/A')
                            project_name = project.get('Project_Name', 'Unnamed Project')[:40]
                            project_number = project.get('Project_Number', 'N/A')
                            
                            with ui.row().classes('items-center gap-2 mt-1'):
                                ui.label(f"{project_number}:").classes('text-xs font-mono text-gray-500')
                                ui.label(project_name).classes('text-xs text-gray-700 truncate')
                        
                        if len(summary['projects']) > 3:
                            ui.label(f"... and {len(summary['projects']) - 3} more").classes('text-xs text-gray-500 mt-1')


@ui.page('/status/{category}')
def status_category_view(category: str):
    """View projects in a specific status category"""
    
    if category not in pmbok_viewer.project_status_categories:
        ui.label(f"Invalid status category: {category}").classes('text-red-500 text-xl')
        return
    
    category_info = pmbok_viewer.project_status_categories[category]
    projects = pmbok_viewer.get_projects_by_status_category(category)
    sorted_projects = pmbok_viewer.sort_projects_by_due_date(projects)
    
    ui.page_title(f"{category_info['name']} Projects")
    
    with ui.row().classes('w-full'):
        # Header
        with ui.card().classes('w-full'):
            with ui.row().classes('items-center gap-3'):
                ui.icon(category_info['icon']).classes(f'text-{category_info["color"]}-500 text-4xl')
                with ui.column():
                    ui.label(category_info['name']).classes('text-3xl font-bold')
                    ui.label(category_info['description']).classes('text-lg text-gray-600')
                    ui.label(f"{len(projects)} projects (sorted by due date)").classes(f'text-{category_info["color"]}-600 font-semibold')
    
    # Navigation buttons
    with ui.row().classes('w-full justify-center gap-4 mb-6'):
        ui.button('Portfolio Overview', on_click=lambda: ui.navigate.to('/')).classes('bg-blue-500 text-white')
        ui.button('Status Dashboard', on_click=lambda: ui.navigate.to('/status-dashboard')).classes('bg-purple-500 text-white')
        ui.button('PMBOK Analysis', on_click=lambda: ui.navigate.to('/pmbok-report')).classes('bg-green-500 text-white')
    
    # Project cards
    if sorted_projects:
        with ui.grid(columns=2).classes('w-full gap-4'):
            for project in sorted_projects:
                project_id = project.get('Project_ID', 'N/A')
                project_name = project.get('Project_Name', 'Unnamed Project')
                assigned_to = project.get('Project_Team_Lead', 'Unassigned')
                status = pmbok_viewer.get_project_effective_status(project)
                due_date_raw = project.get('Required_Date', 'Not specified')
                
                # Format due date for display
                if isinstance(due_date_raw, (int, float)):
                    from datetime import datetime
                    try:
                        due_date = datetime.fromtimestamp(due_date_raw / 1000).strftime('%Y-%m-%d')
                    except:
                        due_date = "Not specified"
                else:
                    due_date = str(due_date_raw) if due_date_raw else "Not specified"
                
                # Calculate days until due
                days_until_due = pmbok_viewer.calculate_days_until_due(project)
                due_status, due_color = pmbok_viewer.get_due_date_status(days_until_due)
                
                with ui.card().classes(f'hover:shadow-lg transition-shadow border-l-4 border-{category_info["color"]}-500'):
                    with ui.card_section():
                        # Show Project Number instead of Project ID
                        project_number = project.get('Project_Number', 'N/A')
                        ui.label(f"{project_number}: {project_name}").classes('text-lg font-bold')
                        ui.label(f"Status: {status}").classes(f'text-{category_info["color"]}-600 font-medium')
                        ui.label(f"Lead: {assigned_to}").classes('text-gray-700')
                        ui.label(f"Due: {due_date}").classes('text-gray-600')
                        
                        # Due date status badge
                        if days_until_due is not None:
                            ui.badge(due_status).classes(f'bg-{due_color}-500 text-white text-sm mt-1')
                        
                        with ui.row().classes('gap-2 mt-3'):
                            ui.button('View Details', 
                                    on_click=lambda pid=project_id: ui.navigate.to(f'/project/{pid}')
                            ).classes('bg-blue-500 text-white')
                            ui.button('PMBOK Analysis', 
                                    on_click=lambda pid=project_id: ui.navigate.to(f'/pmbok/{pid}')
                            ).classes('bg-green-500 text-white')
                            ui.button('Edit Status', 
                                    on_click=lambda pid=project_id: ui.navigate.to(f'/edit-status/{pid}')
                            ).classes('bg-orange-500 text-white')
    else:
        with ui.card().classes('w-full text-center'):
            ui.label(f"No projects currently in {category_info['name']} status").classes('text-gray-500 text-lg')


@ui.page('/edit-status/{project_id}')
def edit_project_status(project_id: str):
    """Edit project status page"""
    
    # Find the project
    project = next((p for p in pmbok_viewer.projects if str(p.get('Project_ID', '')) == str(project_id)), None)
    if not project:
        ui.label(f"Project {project_id} not found").classes('text-red-500 text-xl')
        return
    
    project_name = project.get('Project_Name', 'Unnamed Project')
    project_number = project.get('Project_Number', 'N/A')
    current_status = pmbok_viewer.get_project_effective_status(project)
    original_status = project.get('Project_Status', 'Unknown')
    
    ui.page_title(f"Edit Status - {project_name}")
    
    with ui.card().classes('w-full max-w-2xl mx-auto'):
        with ui.card_section():
            # Show Project Number instead of Project ID
            project_number = project.get('Project_Number', 'N/A')
            ui.label(f"Edit Status for Project {project_number}").classes('text-2xl font-bold')
            ui.label(project_name).classes('text-lg text-gray-600')
            
            ui.separator()
            
            ui.label(f"Original ArcGIS Status: {original_status}").classes('text-sm text-gray-500')
            ui.label(f"Current Effective Status: {current_status}").classes('text-sm font-medium')
            
            # Status override info
            if str(project_id) in pmbok_viewer.status_overrides:
                override_info = pmbok_viewer.status_overrides[str(project_id)]
                ui.label(f"Last updated: {override_info.get('updated_at', 'Unknown')} by {override_info.get('updated_by', 'Unknown')}").classes('text-xs text-gray-400')
            
            ui.separator()
            
            # Status selection
            ui.label("Select New Status:").classes('text-lg font-semibold mt-4')
            
            with ui.column().classes('gap-2 mt-2'):
                selected_status = {'value': current_status}
                
                for category_key, category_info in pmbok_viewer.project_status_categories.items():
                    with ui.expansion(category_info['name']).classes('w-full'):
                        with ui.column().classes('gap-1 p-2'):
                            ui.label(category_info['description']).classes('text-sm text-gray-600 mb-2')
                            
                            for status in category_info['statuses']:
                                with ui.row().classes('items-center gap-2'):
                                    ui.radio([status], value=current_status if status == current_status else None, 
                                           on_change=lambda e, s=status: selected_status.update({'value': s})).classes('flex-none')
                                    ui.label(status).classes('flex-1')
            
            ui.separator()
            
            # Action buttons
            with ui.row().classes('justify-between mt-4'):
                ui.button('Cancel', on_click=lambda: ui.navigate.to(f'/project/{project_id}')).classes('bg-gray-500 text-white')
                
                def save_status():
                    new_status = selected_status['value']
                    if new_status != current_status:
                        success = pmbok_viewer.update_project_status(project_id, new_status)
                        if success:
                            ui.notify(f'Status updated to: {new_status}', type='positive')
                            ui.navigate.to(f'/project/{project_id}')
                        else:
                            ui.notify('Failed to save status update', type='negative')
                    else:
                        ui.navigate.to(f'/project/{project_id}')
                
                ui.button('Save Status', on_click=save_status).classes('bg-green-500 text-white')
                
                # Reset to original button
                def reset_status():
                    if str(project_id) in pmbok_viewer.status_overrides:
                        del pmbok_viewer.status_overrides[str(project_id)]
                        pmbok_viewer.save_status_overrides()
                        ui.notify('Status reset to original ArcGIS value', type='positive')
                        ui.navigate.to(f'/project/{project_id}')
                    else:
                        ui.notify('No override to reset', type='info')
                
                if str(project_id) in pmbok_viewer.status_overrides:
                    ui.button('Reset to Original', on_click=reset_status).classes('bg-orange-500 text-white')


@ui.page('/')
def pmbok_dashboard():
    """PMBOK-aligned project portfolio dashboard"""
    
    # Header with PMBOK branding
    with ui.row().classes('w-full justify-center mb-6'):
        with ui.column().classes('text-center'):
            ui.label('🦌 Caribou Portal - PMBOK Project Portfolio').classes('text-4xl font-bold text-blue-700')
            ui.label('PMI PMBOK 7th Edition Aligned Dashboard').classes('text-lg text-gray-600')
    
    # Portfolio metrics
    metrics_container = ui.row().classes('w-full justify-center gap-4 mb-6')
    
    # Process Groups distribution
    process_container = ui.row().classes('w-full justify-center gap-4 mb-6')
    
    # Main project grid
    projects_container = ui.column().classes('w-full px-4')
    
    def update_dashboard():
        """Update dashboard with latest PMBOK metrics"""
        import subprocess
        import os
        
        try:
            # First show notification before any UI changes
            print('🔄 Refreshing portfolio data...')
            
            # Run enhanced_get_projects_s3.py to get latest data
            script_path = os.path.join(os.path.dirname(__file__), 'enhanced_get_projects_s3.py')
            if os.path.exists(script_path):
                try:
                    # Use the same Python environment that's running this dashboard
                    result = subprocess.run([sys.executable, script_path], 
                                          capture_output=True, text=True, timeout=120)
                    if result.returncode == 0:
                        print(f"✅ enhanced_get_projects_s3.py executed successfully")
                        print(f"Output: {result.stdout[-200:]}")  # Show last 200 chars of output
                    else:
                        print(f"Warning: enhanced_get_projects_s3.py failed: {result.stderr}")
                except subprocess.TimeoutExpired:
                    print("Warning: enhanced_get_projects_s3.py timed out")
                except Exception as e:
                    print(f"Warning: Could not run enhanced_get_projects_s3.py: {e}")
            else:
                print(f"Warning: enhanced_get_projects_s3.py not found at {script_path}")
            
            # Refresh the PMBOK viewer data
            count = pmbok_viewer.refresh_data()
            metrics = pmbok_viewer.get_project_metrics()
            
            # Clear containers
            metrics_container.clear()
            process_container.clear()
            projects_container.clear()
            
            # Portfolio KPIs
            with metrics_container:
                with ui.card().classes('p-4 bg-blue-50'):
                    ui.label(f'📊 Total Portfolio: {metrics.get("total_projects", 0)}').classes('text-lg font-semibold text-blue-700')
                
                with ui.card().classes('p-4 bg-green-50 cursor-help').tooltip('On Track: Projects with more than 7 days remaining until due date and Schedule Performance Index (SPI) ≥ 0.9'):
                    ui.label(f'✅ On Track: {metrics.get("on_track_count", 0)}').classes('text-lg font-semibold text-green-700')
                
                with ui.card().classes('p-4 bg-yellow-50 cursor-help').tooltip('At Risk: Projects with 7 days or less until due date, OR projects with Schedule Performance Index (SPI) < 0.9 (behind schedule)'):
                    ui.label(f'⚠️ At Risk: {metrics.get("at_risk_count", 0)}').classes('text-lg font-semibold text-yellow-700')
                
                with ui.card().classes('p-4 bg-red-50 cursor-help').tooltip('Overdue: Projects where the due date has already passed (remaining days < 0)'):
                    ui.label(f'🚨 Overdue: {metrics.get("overdue_count", 0)}').classes('text-lg font-semibold text-red-700')
            
            # PMBOK Process Groups
            with process_container:
                ui.label('PMBOK Process Groups Distribution:').classes('text-xl font-bold text-gray-700 w-full text-center mb-2')
                
                # Process group tooltip definitions
                process_tooltips = {
                    'initiating': 'Initiating: Projects in the early startup phase, defining project scope, objectives, and stakeholders',
                    'planning': 'Planning: Projects developing detailed project management plans, schedules, budgets, and resource allocation',
                    'executing': 'Executing: Projects actively performing the work defined in the project management plan',
                    'monitoring': 'Monitoring & Controlling: Projects tracking progress, managing changes, and ensuring deliverables meet quality standards',
                    'closing': 'Closing: Projects completing final deliverables, obtaining stakeholder approval, and formal project closure'
                }
                
                process_dist = metrics.get('process_distribution', {})
                for process_key, count in process_dist.items():
                    if count > 0:
                        process_name = pmbok_viewer.process_groups.get(process_key, process_key)
                        tooltip_text = process_tooltips.get(process_key, f'{process_name}: PMBOK process group')
                        
                        with ui.card().classes('p-3 bg-gray-50 cursor-help').tooltip(tooltip_text):
                            ui.label(f'{process_name}: {count}').classes('text-sm font-medium text-gray-700')
            
            # Project cards
            display_pmbok_projects()
            
            # Update Dendron main note if vault is available
            try:
                dendron_status = pmbok_viewer.get_dendron_integration_status()
                if dendron_status.get('vault_found') and dendron_status.get('can_read'):
                    pmbok_viewer.create_main_caribou_portal_note(dendron_status['vault_path'])
                    print("✅ Updated Dendron main note")
            except Exception as e:
                print(f"Warning: Could not update Dendron note: {e}")
            
            # Final success notification
            print(f'✅ Portfolio refreshed! {count} projects loaded')
            
        except Exception as e:
            print(f'❌ Error refreshing portfolio: {str(e)}')
            print(f"Error in update_dashboard: {e}")
    
    def open_status_update_dialog(project_id: str):
        """Open a dialog to update project status"""
        project = pmbok_viewer.get_project_by_id(project_id)
        if not project:
            ui.notify(f'Project not found', type='negative')
            print(f"DEBUG: Project {project_id} not found")  # Debug line
            return
        
        project_number = project.get('Project_Number', 'N/A')
        print(f"DEBUG: Opening status dialog for project {project_number} (ID: {project_id})")  # Debug line
        
        current_status = pmbok_viewer.get_project_effective_status(project)
        project_name = project.get('Project_Name', 'Unknown Project')
        
        print(f"DEBUG: Project found - {project_name}, current status: {current_status}")  # Debug line
        
        # Define available status options
        status_options = [
            'Not Assigned',
            'Not Started',
            'In Progress', 
            'Client Review',
            'Awaiting Resources',
            'On Hold',
            'Completed'
        ]
        
        # First show a notification to confirm the function is being called
        ui.notify(f'Opening status update for {project_name}', type='info')
        
        with ui.dialog() as dialog, ui.card().classes('w-96 p-4'):
            ui.label(f'Update Status: {project_name}').classes('text-lg font-bold mb-2')
            # Show Project Number instead of Project ID
            project_number = project.get('Project_Number', 'N/A')
            ui.label(f'Project Number: {project_number}').classes('text-sm text-gray-600 mb-4')
            ui.label(f'Current Status: {current_status}').classes('text-sm font-medium mb-4')
            
            status_select = ui.select(
                label='New Status',
                options=status_options,
                value=current_status if current_status in status_options else status_options[0]
            ).classes('w-full mb-4')
            
            with ui.row().classes('w-full justify-end gap-2'):
                ui.button('Cancel', on_click=dialog.close).classes('bg-gray-500 text-white')
                
                def save_status():
                    new_status = status_select.value
                    print(f"DEBUG: Saving status change from {current_status} to {new_status}")  # Debug line
                    
                    if new_status and new_status != current_status:
                        try:
                            success = pmbok_viewer.update_project_status(project_id, new_status)
                            print(f"DEBUG: Update result: {success}")  # Debug line
                            
                            if success:
                                ui.notify(f'✅ Status updated to: {new_status}', type='positive')
                                dialog.close()
                                # Refresh the dashboard to show updated status
                                update_dashboard()
                            else:
                                ui.notify('❌ Failed to save status update', type='negative')
                        except Exception as e:
                            print(f"DEBUG: Error updating status: {e}")  # Debug line
                            ui.notify(f'❌ Error: {str(e)}', type='negative')
                    else:
                        ui.notify('No changes made', type='info')
                        dialog.close()
                
                ui.button('Save', on_click=save_status).classes('bg-blue-500 text-white')
        
        print("DEBUG: Opening dialog")  # Debug line
        dialog.open()

    def display_pmbok_projects():
        """Display projects with PMBOK analysis"""
        if not pmbok_viewer.projects:
            with projects_container:
                ui.label('No projects found. Please run the data collection script first.').classes('text-red-500 text-center text-xl')
            return
        
        with projects_container:
            # Controls
            with ui.row().classes('w-full justify-center mb-4 gap-4'):
                ui.button('🔄 Refresh Portfolio', on_click=update_dashboard).classes('bg-blue-500 text-white px-6 py-2')
                ui.button('📋 Status Dashboard', on_click=lambda: ui.navigate.to('/status-dashboard')).classes('bg-purple-500 text-white px-6 py-2')
                ui.button('📊 PMBOK Report', on_click=lambda: ui.navigate.to('/pmbok-report')).classes('bg-green-500 text-white px-6 py-2')
                # ui.button('👥 Team Engagement', on_click=lambda: ui.navigate.to('/engagement')).classes('bg-orange-500 text-white px-6 py-2')
                ui.button('📝 GSS Caribou Support Information', on_click=lambda: ui.navigate.to('/dendron-integration')).classes('bg-indigo-500 text-white px-6 py-2')
            
            # Project grid with PMBOK metrics (sorted by due date)
            sorted_projects = pmbok_viewer.sort_projects_by_due_date(pmbok_viewer.projects)
            
            # Add sorting indicator
            ui.label('Projects sorted by due date (nearest deadlines first)').classes('text-sm text-gray-600 text-center w-full mb-2')
            
            # Table view for projects (NiceGUI expects columns and rows arguments)
            table_rows = []
            for project in sorted_projects:
                    project_name = project.get('Project_Name', 'N/A')
                    date_required_raw = project.get('Date_Required', None)
                    if isinstance(date_required_raw, (int, float)):
                        from datetime import datetime
                        try:
                            required_date = datetime.fromtimestamp(date_required_raw / 1000).strftime('%Y-%m-%d')
                        except:
                            required_date = "Not specified"
                    else:
                        required_date = str(date_required_raw) if date_required_raw else "Not specified"

                    # Get all people associated: lead and team members
                    people = []
                    lead = project.get('Project_Team_Lead', '') or project.get('Team_Member', '')
                    if lead and lead != 'N/A':
                        people.append(lead)
                    team_members = project.get('Team_Members', [])
                    if isinstance(team_members, list):
                        for member in team_members:
                            if isinstance(member, dict):
                                name = member.get('Resource_Name', '').strip()
                                if name:
                                    people.append(name)
                            elif isinstance(member, str) and member.strip():
                                people.append(member.strip())
                    elif isinstance(team_members, str) and team_members:
                        people.extend([m.strip() for m in team_members.split(',') if m.strip()])
                    # Remove duplicates
                    people_display = ', '.join(dict.fromkeys(people)) if people else 'Unassigned'
                    status = pmbok_viewer.get_project_effective_status(project)
                    
                    # Get status category for color coding
                    status_category = pmbok_viewer.get_project_status_category(project)
                    status_color = pmbok_viewer.project_status_categories[status_category]['color']
                    
                    table_rows.append({
                        'Project Name': project_name,
                        'Required Date': required_date,
                        'Staff Assigned': people_display,
                        'Status': status,
                        'status_color': status_color,
                        'project_id': project.get('Project_ID', '')
                    })
            
            # Create a custom table with color-coded rows
            ui.label('Click on project name/date/people to view details • Click on status to update • Hover over notes field to see full text • Edit notes directly in the field • Add action items (one per line) in Coordinator Actions').classes('text-sm text-gray-600 text-center w-full mb-3 italic')
            with ui.element('div').classes('w-full overflow-x-auto'):
                with ui.element('table').classes('w-full border-collapse bg-white shadow-sm rounded-lg'):
                    # Table header
                    with ui.element('thead').classes('bg-gray-50'):
                        with ui.element('tr'):
                            with ui.element('th').classes('px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-b'):
                                ui.html('Project Name')
                            with ui.element('th').classes('px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-b'):
                                ui.html('Required Date')
                            with ui.element('th').classes('px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-b'):
                                ui.html('Staff Assigned')
                            with ui.element('th').classes('px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-b'):
                                ui.html('Status')
                            with ui.element('th').classes('px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-b'):
                                ui.html('Notes')
                            with ui.element('th').classes('px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-b'):
                                ui.html('Coordinator Actions')
                    
                    # Table body
                    with ui.element('tbody').classes('divide-y divide-gray-200'):
                        for row in table_rows:
                            color = row['status_color']
                            project_id = row['project_id']
                            
                            # Make "Not Assigned" projects extra prominent with bright red styling
                            if row['Status'] in ['Not Assigned', 'Unassigned', 'Pending Assignment']:
                                row_classes = 'hover:bg-red-200 border-l-4 border-red-600 bg-red-100 transition-colors'
                                text_classes = 'text-red-900'
                            else:
                                row_classes = f'hover:bg-{color}-100 border-l-4 border-{color}-500 bg-{color}-50 transition-colors'
                                text_classes = 'text-gray-900'
                            
                            # Create clickable row that navigates to project detail
                            with ui.element('tr').classes(row_classes):
                                with ui.element('td').classes(f'px-6 py-4 whitespace-nowrap text-sm font-medium {text_classes} cursor-pointer').on('click', lambda pid=project_id: ui.navigate.to(f'/pmbok/{pid}')):
                                    ui.html(row['Project Name'])
                                    # Show Project Number instead of Project ID
                                    project_number = next((p.get('Project_Number', 'N/A') for p in pmbok_viewer.projects if str(p.get('Project_ID', '')) == str(project_id)), 'N/A')
                                    ui.html(f'<div class="text-xs text-gray-500">{project_number}</div>')
                                with ui.element('td').classes(f'px-6 py-4 whitespace-nowrap text-sm {text_classes} cursor-pointer').on('click', lambda pid=project_id: ui.navigate.to(f'/pmbok/{pid}')):
                                    ui.html(row['Required Date'])
                                with ui.element('td').classes(f'px-6 py-4 whitespace-nowrap text-sm {text_classes} cursor-pointer').on('click', lambda pid=project_id: ui.navigate.to(f'/pmbok/{pid}')):
                                    ui.html(row['Staff Assigned'])
                                with ui.element('td').classes('px-6 py-4 whitespace-nowrap'):
                                    def update_status_handler(pid=project_id):
                                        open_status_update_dialog(pid)
                                    
                                    # Make status button extra prominent for Not Assigned projects
                                    if row['Status'] in ['Not Assigned', 'Unassigned', 'Pending Assignment']:
                                        button_classes = 'px-2 py-1 text-xs font-bold rounded-full bg-red-600 text-white hover:bg-red-700 transition-colors border-0 shadow-lg'
                                    else:
                                        button_classes = f'px-2 py-1 text-xs font-semibold rounded-full bg-{color}-500 text-white hover:bg-{color}-600 transition-colors border-0'
                                    
                                    ui.button(f'✏️ {row["Status"]}', on_click=update_status_handler).classes(button_classes).props('flat dense')
                                
                                # Notes column with editable textarea and save button
                                with ui.element('td').classes('px-6 py-4 whitespace-nowrap'):
                                    current_notes = pmbok_viewer.get_project_notes(project_id)
                                    
                                    with ui.column().classes('w-full gap-1'):
                                        # Create textarea for notes
                                        notes_textarea = ui.textarea(
                                            label='',
                                            placeholder='Add notes...',
                                            value=current_notes,
                                        ).classes('w-full text-xs').props('dense outlined rows=3')
                                        
                                        # Add save button
                                        def save_notes_click(pid=project_id, textarea=notes_textarea):
                                            def on_save():
                                                new_notes = textarea.value
                                                success = pmbok_viewer.update_project_notes(pid, new_notes)
                                                if success:
                                                    print(f"✅ Notes saved for project {pid}: '{new_notes[:50]}...'")
                                                    ui.notify(f'Notes saved for {row["Project_Name"][:30]}...', type='positive')
                                                else:
                                                    print(f"❌ Failed to save notes for project {pid}")
                                                    ui.notify('Failed to save notes', type='negative')
                                            return on_save
                                        
                                        ui.button('💾', on_click=save_notes_click()).classes('text-xs bg-blue-500 text-white px-2 py-1').props('dense')
                                        
                                        # Show hover tooltip for existing notes
                                        if current_notes:
                                            notes_textarea.tooltip(current_notes)
                                
                                # Coordinator Actions column with editable textarea and save button (bulleted list)
                                with ui.element('td').classes('px-6 py-4 whitespace-nowrap'):
                                    current_actions = pmbok_viewer.get_coordinator_actions(project_id)
                                    
                                    with ui.column().classes('w-full gap-1'):
                                        # Create textarea for actions
                                        actions_textarea = ui.textarea(
                                            label='',
                                            placeholder='Add action items...\nOne per line',
                                            value=current_actions,
                                        ).classes('w-full text-xs').props('dense outlined rows=3')
                                        
                                        # Add save button
                                        def save_actions_click(pid=project_id, textarea=actions_textarea):
                                            def on_save():
                                                new_actions = textarea.value
                                                success = pmbok_viewer.update_coordinator_actions(pid, new_actions)
                                                if success:
                                                    print(f"✅ Coordinator actions saved for project {pid}: '{new_actions[:50]}...'")
                                                    ui.notify(f'Actions saved for {row["Project_Name"][:30]}...', type='positive')
                                                else:
                                                    print(f"❌ Failed to save coordinator actions for project {pid}")
                                                    ui.notify('Failed to save actions', type='negative')
                                            return on_save
                                        
                                        ui.button('💾', on_click=save_actions_click()).classes('text-xs bg-green-500 text-white px-2 py-1').props('dense')
                                        
                                        # Show hover tooltip for existing actions (formatted as bullets)
                                        if current_actions:
                                            display_actions = pmbok_viewer.format_actions_as_bullets(current_actions)
                                            actions_textarea.tooltip(display_actions)
    
    def create_pmbok_project_card(project: Dict[str, Any]):
        """Create enhanced PMBOK-aligned project card with team, dates, and status"""
        project_id = project.get('Project_ID', '')
        project_name = project.get('Project_Name', 'N/A')
        project_number = project.get('Project_Number', 'N/A')
        
        # Get effective status and team information
        effective_status = pmbok_viewer.get_project_effective_status(project)
        team_members = pmbok_viewer.get_team_members_list(project)
        days_until_due = pmbok_viewer.calculate_days_until_due(project)
        due_status, due_color = pmbok_viewer.get_due_date_status(days_until_due)
        
        # PMBOK Analysis
        phase = pmbok_viewer.get_project_phase(project)
        phase_name = pmbok_viewer.process_groups.get(phase, phase)
        schedule_perf = pmbok_viewer.calculate_schedule_performance(project)
        risk_analysis = pmbok_viewer.get_risk_level(project)
        
        # Card styling based on due date urgency
        if days_until_due is not None and days_until_due <= 0:
            border_color = 'border-red-500'
            card_bg = 'bg-red-50'
        elif days_until_due is not None and days_until_due <= 7:
            border_color = 'border-yellow-500'
            card_bg = 'bg-yellow-50'
        else:
            border_color = f'border-{schedule_perf["health"]}-400'
            card_bg = 'bg-white'
        
        with ui.card().classes(f'w-80 p-4 cursor-pointer hover:shadow-lg transition-shadow border-l-4 {border_color} {card_bg}'):
            # Header with project info and status
            with ui.row().classes('w-full justify-between items-start mb-3'):
                with ui.column().classes('flex-grow'):
                    ui.label(project_name).classes('text-lg font-bold text-gray-800 leading-tight')
                    ui.label(project_number).classes('text-sm text-gray-600')
                
                with ui.column().classes('text-right'):
                    # Status badge
                    status_category = pmbok_viewer.get_project_status_category(project)
                    status_color = pmbok_viewer.project_status_categories[status_category]['color']
                    ui.badge(effective_status).classes(f'bg-{status_color}-500 text-white text-xs mb-1')
                    
                    # Phase badge
                    ui.badge(phase_name).classes('bg-blue-500 text-white text-xs')
            
            # Due date information (prominent display)
            with ui.row().classes('w-full items-center mb-3 p-2 bg-white rounded'):
                ui.icon('event').classes(f'text-{due_color}-600 mr-2')
                if days_until_due is not None:
                    due_date_raw = project.get('Date_Required', '') or project.get('Required_Date', '')
                    
                    # Format the due date for display
                    if isinstance(due_date_raw, (int, float)):
                        from datetime import datetime
                        try:
                            formatted_date = datetime.fromtimestamp(due_date_raw / 1000).strftime('%Y-%m-%d')
                        except:
                            formatted_date = "Unknown"
                    else:
                        formatted_date = str(due_date_raw).split("T")[0] if due_date_raw else "Unknown"
                    
                    ui.label(f'Due: {formatted_date}').classes('text-sm text-gray-700 mr-2')
                    ui.badge(due_status).classes(f'bg-{due_color}-500 text-white text-xs')
                else:
                    ui.label('Due: Not specified').classes('text-sm text-gray-500')
            
            # Team members section
            with ui.row().classes('w-full items-start mb-3'):
                ui.icon('people').classes('text-gray-600 mr-1 mt-0.5')
                with ui.column().classes('flex-grow'):
                    ui.label('Team:').classes('text-sm font-semibold text-gray-700 mb-1')
                    for i, member in enumerate(team_members[:3]):  # Show max 3 members
                        ui.label(f'• {member}').classes('text-xs text-gray-600')
                    if len(team_members) > 3:
                        ui.label(f'• ... +{len(team_members) - 3} more').classes('text-xs text-gray-500')
            
            # PMBOK metrics row
            with ui.row().classes('w-full items-center mb-2 text-xs'):
                with ui.column().classes('flex-1'):
                    ui.label(f'SPI: {schedule_perf.get("spi", "N/A")}').classes('text-gray-600')
                    ui.label(f'Risk: {risk_analysis["level"]}').classes(f'text-{risk_analysis["color"]}-600')
                
                with ui.column().classes('flex-1 text-right'):
                    client = project.get('Client_Name', 'N/A')[:20]
                    ui.label(f'Client: {client}').classes('text-gray-600')
                    priority = project.get('Priority_Level', 'N/A')
                    ui.label(f'Priority: {priority}').classes('text-gray-600')
            
            # Actions
            with ui.row().classes('w-full gap-2 mt-3'):
                ui.button('📋 Details', 
                         on_click=lambda p_id=project_id: ui.navigate.to(f'/project/{p_id}')
                         ).classes('flex-1 bg-blue-600 text-white text-sm')
                ui.button('📊 PMBOK', 
                         on_click=lambda p_id=project_id: ui.navigate.to(f'/pmbok/{p_id}')
                         ).classes('flex-1 bg-green-600 text-white text-sm')
                ui.button('✏️', 
                         on_click=lambda p_id=project_id: ui.navigate.to(f'/edit-status/{p_id}')
                         ).classes('bg-orange-600 text-white text-sm px-2')
    
    # Initial load
    update_dashboard()


@ui.page('/project/{project_id}')
def project_detail(project_id: str):
    """Basic project details view (redirects to PMBOK analysis)"""
    
    # Refresh data to ensure we have latest
    pmbok_viewer.refresh_data()
    project = pmbok_viewer.get_project_by_id(project_id)
    
    if not project:
        with ui.column().classes('w-full max-w-4xl mx-auto p-8'):
            ui.label('❌ Project not found').classes('text-2xl text-red-500 text-center')
            ui.button('← Back to Portfolio', on_click=lambda: ui.navigate.to('/')).classes('bg-blue-500 text-white mt-4')
        return
    
    # Header
    with ui.row().classes('w-full max-w-6xl mx-auto p-4 items-center'):
        ui.button('← Back to Portfolio', on_click=lambda: ui.navigate.to('/')).classes('bg-blue-500 text-white mr-4')
        ui.label(f'📋 Project Details').classes('text-3xl font-bold text-blue-700')
        ui.button('📊 View PMBOK Analysis', on_click=lambda: ui.navigate.to(f'/pmbok/{project_id}')).classes('bg-green-500 text-white ml-4')
    
    # Main content - simplified project view
    with ui.column().classes('w-full max-w-6xl mx-auto p-4'):
        
        # Project header card
        with ui.card().classes('w-full p-6 mb-6 border-l-4 border-blue-500'):
            with ui.row().classes('w-full justify-between items-start'):
                with ui.column().classes('flex-grow'):
                    ui.label(project.get('Project_Name', 'N/A')).classes('text-2xl font-bold text-blue-700 mb-2')
                    ui.label(f"Project Number: {project.get('Project_Number', 'N/A')}").classes('text-lg text-gray-600')
                
                status = pmbok_viewer.get_project_effective_status(project)
                original_status = project.get('Project_Status', 'Unknown')
                status_color = pmbok_viewer.get_status_color(status)
                
                with ui.column().classes('items-end'):
                    ui.badge(status).classes(f'{status_color} text-white text-lg px-4 py-2')
                    
                    # Show if status is overridden
                    if str(project_id) in pmbok_viewer.status_overrides:
                        ui.label(f"(Original: {original_status})").classes('text-xs text-gray-500 mt-1')
                    
                    ui.button('✏️ Edit Status', on_click=lambda: ui.navigate.to(f'/edit-status/{project_id}')).classes('bg-orange-500 text-white text-sm mt-2')
        
        # Key information row
        with ui.row().classes('w-full gap-6 mb-6'):
            # Left column - Project Info
            with ui.card().classes('flex-1 p-6'):
                ui.label('📋 Project Information').classes('text-xl font-bold mb-4 text-blue-700')
                
                info_items = [
                    ('Client Name', project.get('Client_Name', 'N/A')),
                    ('Client Email', project.get('Client_Email', 'N/A')),
                    ('Ministry', project.get('Ministry', 'N/A')),
                    ('Program/Division', project.get('Program_Division', 'N/A')),
                    ('Priority Level', project.get('Priority_Level', 'N/A')),
                    ('Request Type', project.get('Request_Type', 'N/A')),
                    ('Date Requested', pmbok_viewer.format_date(project.get('Date_Requested'))),
                    ('Date Required', pmbok_viewer.format_date(project.get('Date_Required'))),
                ]
                
                for label, value in info_items:
                    with ui.row().classes('mb-2'):
                        ui.label(f'{label}:').classes('font-semibold text-gray-700 w-32')
                        ui.label(value).classes('text-gray-900')
            
            # Right column - Team & Resources
            with ui.card().classes('flex-1 p-6'):
                ui.label('👥 Team & Resources').classes('text-xl font-bold mb-4 text-blue-700')
                
                # Team members
                ui.label('Team Members:').classes('font-semibold text-gray-700 mb-2')
                ui.label('• Cole Folkers (Coordinator)').classes('text-gray-900 ml-4')
                
                team_members = project.get('Team_Members', [])
                if team_members:
                    for member in team_members:
                        name = member.get('Resource_Name', 'Unknown')
                        email = member.get('Resource_Contact_Email', '')
                        team = member.get('Resource_Team', '')
                        ui.label(f'• {name}').classes('text-gray-900 ml-4')
                        if email:
                            ui.label(f'  Email: {email}').classes('text-gray-600 ml-8 text-sm')
                        if team:
                            ui.label(f'  Team: {team}').classes('text-gray-600 ml-8 text-sm')
                else:
                    ui.label('No additional team members assigned').classes('text-gray-600 ml-4 italic')
                
                # Project hours if available
                if project.get('Project_Hours'):
                    ui.label(f'Allocated Hours: {project.get("Project_Hours")}').classes('text-gray-900 mt-4 font-medium')
                
                # Geospatial info
                geospatial_team = project.get('Geospatial_Team', '')
                geospatial_type = project.get('Geospatial_Type', '')
                if geospatial_team:
                    ui.label(f'Geospatial Team: {geospatial_team}').classes('text-gray-900 mt-2')
                if geospatial_type:
                    ui.label(f'Geospatial Type: {geospatial_type}').classes('text-gray-900 mt-1')
        
        # Project Description
        if project.get('Project_Description'):
            with ui.card().classes('w-full p-6 mb-6'):
                ui.label('📝 Project Description').classes('text-xl font-bold mb-4 text-blue-700')
                ui.label(project.get('Project_Description', '')).classes('text-gray-800 whitespace-pre-wrap leading-relaxed')
        
        # Project Notes Section
        with ui.card().classes('w-full p-6 mb-6'):
            ui.label('📋 Project Notes').classes('text-xl font-bold mb-4 text-blue-700')
            
            current_notes = pmbok_viewer.get_project_notes(project_id)
            
            def save_notes_from_detail():
                def on_notes_change(e):
                    new_notes = e.value
                    success = pmbok_viewer.update_project_notes(project_id, new_notes)
                    if success:
                        ui.notify(f'✅ Notes saved successfully', type='positive')
                        print(f"✅ Notes saved for project {project_id} from detail page")
                    else:
                        ui.notify(f'❌ Failed to save notes', type='negative')
                        print(f"❌ Failed to save notes for project {project_id}")
                return on_notes_change
            
            if current_notes:
                ui.label('Current Notes:').classes('font-semibold text-gray-700 mb-2')
                ui.label(current_notes).classes('text-gray-800 mb-4 p-3 bg-gray-50 rounded border-l-4 border-blue-400 whitespace-pre-wrap')
            
            ui.label('Edit Notes:').classes('font-semibold text-gray-700 mb-2')
            
            with ui.column().classes('w-full gap-3'):
                notes_textarea_detail = ui.textarea(
                    label='',
                    placeholder='Add or edit project notes here...',
                    value=current_notes,
                ).classes('w-full').props('outlined rows=4')
                
                def save_notes_click_detail():
                    def on_save():
                        new_notes = notes_textarea_detail.value
                        success = pmbok_viewer.update_project_notes(project_id, new_notes)
                        if success:
                            ui.notify(f'✅ Notes saved successfully', type='positive')
                            print(f"✅ Notes saved for project {project_id} from detail page")
                        else:
                            ui.notify(f'❌ Failed to save notes', type='negative')
                            print(f"❌ Failed to save notes for project {project_id}")
                    return on_save
                
                ui.button('💾', on_click=save_notes_click_detail()).classes('bg-blue-500 text-white px-4 py-2 self-start')
            
            ui.label('Notes will appear in the main project list after saving.').classes('text-xs text-gray-500 mt-2 italic')
        
        # Coordinator Actions Section
        with ui.card().classes('w-full p-6 mb-6'):
            ui.label('🎯 Coordinator Actions').classes('text-xl font-bold mb-4 text-blue-700')
            
            current_actions = pmbok_viewer.get_coordinator_actions(project_id)
            
            def save_actions_from_detail():
                def on_actions_change(e):
                    new_actions = e.value
                    success = pmbok_viewer.update_coordinator_actions(project_id, new_actions)
                    if success:
                        ui.notify(f'✅ Coordinator actions saved successfully', type='positive')
                        print(f"✅ Coordinator actions saved for project {project_id} from detail page")
                    else:
                        ui.notify(f'❌ Failed to save coordinator actions', type='negative')
                        print(f"❌ Failed to save coordinator actions for project {project_id}")
                return on_actions_change
            
            if current_actions:
                ui.label('Current Action Items:').classes('font-semibold text-gray-700 mb-2')
                # Display as bulleted list
                formatted_actions = pmbok_viewer.format_actions_as_bullets(current_actions)
                ui.label(formatted_actions).classes('text-gray-800 mb-4 p-3 bg-gray-50 rounded border-l-4 border-green-400 whitespace-pre-wrap')
            
            ui.label('Edit Action Items:').classes('font-semibold text-gray-700 mb-2')
            
            with ui.column().classes('w-full gap-3'):
                actions_textarea_detail = ui.textarea(
                    label='',
                    placeholder='Add action items here...\nOne item per line\nThey will be displayed as bullets',
                    value=current_actions,
                ).classes('w-full').props('outlined rows=6')
                
                def save_actions_click_detail():
                    def on_save():
                        new_actions = actions_textarea_detail.value
                        success = pmbok_viewer.update_coordinator_actions(project_id, new_actions)
                        if success:
                            ui.notify(f'✅ Coordinator actions saved successfully', type='positive')
                            print(f"✅ Coordinator actions saved for project {project_id} from detail page")
                        else:
                            ui.notify(f'❌ Failed to save coordinator actions', type='negative')
                            print(f"❌ Failed to save coordinator actions for project {project_id}")
                    return on_save
                
                ui.button('💾', on_click=save_actions_click_detail()).classes('bg-green-500 text-white px-4 py-2 self-start')
            
            ui.label('Action items will appear as bullets in the main project list after saving.').classes('text-xs text-gray-500 mt-2 italic')
        
        # Final Deliverables
        if project.get('Final_Deliverables'):
            with ui.card().classes('w-full p-6 mb-6'):
                ui.label('🎯 Final Deliverables').classes('text-xl font-bold mb-4 text-blue-700')
                ui.label(project.get('Final_Deliverables', '')).classes('text-gray-800 whitespace-pre-wrap leading-relaxed')
        
        # Call-to-action for PMBOK analysis
        with ui.card().classes('w-full p-6 bg-green-50 border-l-4 border-green-500'):
            with ui.row().classes('w-full items-center justify-between'):
                with ui.column():
                    ui.label('📊 Want detailed PMBOK analysis?').classes('text-lg font-bold text-green-700')
                    ui.label('View schedule performance, risk analysis, stakeholder management, and more!').classes('text-green-600')
                ui.button('View PMBOK Analysis →', 
                         on_click=lambda: ui.navigate.to(f'/pmbok/{project_id}')
                         ).classes('bg-green-600 text-white px-6 py-3')


@ui.page('/pmbok/{project_id}')
def pmbok_project_view(project_id: str):
    """PMBOK-focused project analysis view"""
    
    pmbok_viewer.refresh_data()
    project = pmbok_viewer.get_project_by_id(project_id)
    
    if not project:
        with ui.column().classes('w-full max-w-4xl mx-auto p-8'):
            ui.label('❌ Project not found').classes('text-2xl text-red-500 text-center')
            ui.button('← Back to Portfolio', on_click=lambda: ui.navigate.to('/')).classes('bg-blue-500 text-white mt-4')
        return
    
    # PMBOK Analysis
    phase = pmbok_viewer.get_project_phase(project)
    phase_name = pmbok_viewer.process_groups.get(phase, phase)
    schedule_perf = pmbok_viewer.calculate_schedule_performance(project)
    risk_analysis = pmbok_viewer.get_risk_level(project)
    stakeholders = pmbok_viewer.get_stakeholder_analysis(project)
    
    # Header
    with ui.row().classes('w-full max-w-6xl mx-auto p-4 items-center'):
        ui.button('← Back to Portfolio', on_click=lambda: ui.navigate.to('/')).classes('bg-blue-500 text-white mr-4')
        ui.label(f'📊 PMBOK Project Analysis').classes('text-3xl font-bold text-blue-700')
    
    with ui.column().classes('w-full max-w-6xl mx-auto p-4'):
        
        # Project Overview
        with ui.card().classes('w-full p-6 mb-6 border-l-4 border-blue-500'):
            ui.label(project.get('Project_Name', 'N/A')).classes('text-2xl font-bold text-blue-700 mb-2')
            # Show Project Number
            project_number = project.get('Project_Number', 'N/A')
            ui.label(f'Project Number: {project_number}').classes('text-lg text-gray-600 mb-4')
            
            with ui.row().classes('w-full gap-4'):
                ui.badge(f'Process Group: {phase_name}').classes('bg-blue-500 text-white px-4 py-2')
                ui.badge(f'Risk Level: {risk_analysis["level"]}').classes(f'bg-{risk_analysis["color"]}-500 text-white px-4 py-2')
                ui.badge(f'Schedule Health: {schedule_perf["status"]}').classes(f'bg-{schedule_perf["health"]}-500 text-white px-4 py-2')
        
        # PMBOK Knowledge Areas
        with ui.row().classes('w-full gap-6 mb-6'):
            
            # Schedule Management
            with ui.card().classes('flex-1 p-6'):
                ui.label('📅 Schedule Management').classes('text-xl font-bold mb-4 text-blue-700')
                
                schedule_items = [
                    ('Schedule Performance Index (SPI)', schedule_perf['spi']),
                    ('Schedule Status', schedule_perf['status']),
                    ('Variance (Days)', schedule_perf['variance_days']),
                    ('Total Duration (Days)', schedule_perf.get('total_duration', 'N/A')),
                    ('Elapsed Duration (Days)', schedule_perf.get('elapsed_duration', 'N/A')),
                    ('Remaining Duration (Days)', schedule_perf.get('remaining_duration', 'N/A')),
                ]
                
                for label, value in schedule_items:
                    with ui.row().classes('mb-2'):
                        ui.label(f'{label}:').classes('font-semibold text-gray-700 w-48')
                        ui.label(str(value)).classes('text-gray-900')
            
            # Risk Management
            with ui.card().classes('flex-1 p-6'):
                ui.label('⚠️ Risk Management').classes('text-xl font-bold mb-4 text-blue-700')
                
                risk_items = [
                    ('Overall Risk Level', risk_analysis['level']),
                    ('Risk Score', f"{risk_analysis['score']}/10"),
                    ('Schedule Risk', schedule_perf['health'].title()),
                    ('Priority Level', project.get('Priority_Level', 'N/A')),
                    ('Team Size Risk', 'Single Person' if len(project.get('Team_Members', [])) == 0 else 'Multi-person'),
                ]
                
                for label, value in risk_items:
                    with ui.row().classes('mb-2'):
                        ui.label(f'{label}:').classes('font-semibold text-gray-700 w-32')
                        ui.label(str(value)).classes('text-gray-900')
        
        # Resource & Stakeholder Management
        with ui.row().classes('w-full gap-6 mb-6'):
            
            # Resource Management
            with ui.card().classes('flex-1 p-6'):
                ui.label('👥 Resource Management').classes('text-xl font-bold mb-4 text-blue-700')
                
                ui.label('Project Team:').classes('font-semibold text-gray-700 mb-2')
                ui.label('• Cole Folkers (Coordinator)').classes('text-gray-900 ml-4')
                
                for member in project.get('Team_Members', []):
                    name = member.get('Resource_Name', 'Unknown')
                    team = member.get('Resource_Team', '')
                    ui.label(f'• {name} (Team Member)').classes('text-gray-900 ml-4')
                    if team:
                        ui.label(f'  Team: {team}').classes('text-gray-600 ml-8 text-sm')
                
                # Project Hours if available
                if project.get('Project_Hours'):
                    ui.label(f'Allocated Hours: {project.get("Project_Hours")}').classes('text-gray-900 mt-4 font-medium')
            
            # Stakeholder Management
            with ui.card().classes('flex-1 p-6'):
                ui.label('🤝 Stakeholder Management').classes('text-xl font-bold mb-4 text-blue-700')
                
                ui.label('Primary Stakeholders:').classes('font-semibold text-gray-700 mb-2')
                for stakeholder in stakeholders['primary']:
                    ui.label(f'• {stakeholder["name"]} ({stakeholder["role"]})').classes('text-gray-900 ml-4 text-sm')
                    ui.label(f'  Influence: {stakeholder["influence"]}, Interest: {stakeholder["interest"]}').classes('text-gray-600 ml-6 text-xs')
        
        # Quality & Communications Management
        with ui.card().classes('w-full p-6 mb-6'):
            ui.label('📋 Quality & Communications Management').classes('text-xl font-bold mb-4 text-blue-700')
            
            with ui.row().classes('w-full gap-8'):
                with ui.column().classes('flex-1'):
                    ui.label('Quality Criteria:').classes('font-semibold text-gray-700 mb-2')
                    if project.get('Final_Deliverables'):
                        ui.label('Defined deliverables and acceptance criteria').classes('text-green-600 ml-4')
                    else:
                        ui.label('No formal deliverables defined').classes('text-red-600 ml-4')
                    
                    geospatial_type = project.get('Geospatial_Type', '')
                    if geospatial_type:
                        ui.label(f'Technical Requirements: {geospatial_type}').classes('text-gray-900 ml-4')
                
                with ui.column().classes('flex-1'):
                    ui.label('Communications Plan:').classes('font-semibold text-gray-700 mb-2')
                    client_email = project.get('Client_Email', '')
                    if client_email:
                        ui.label(f'Primary Contact: {client_email}').classes('text-gray-900 ml-4')
                    
                    ministry = project.get('Ministry', '')
                    if ministry:
                        ui.label(f'Organizational Unit: {ministry}').classes('text-gray-900 ml-4')
        
        # Scope & Integration Management
        if project.get('Project_Description') or project.get('Final_Deliverables'):
            with ui.card().classes('w-full p-6'):
                ui.label('🎯 Scope & Integration Management').classes('text-xl font-bold mb-4 text-blue-700')
                
                if project.get('Project_Description'):
                    ui.label('Project Scope:').classes('font-semibold text-gray-700 mb-2')
                    ui.label(project.get('Project_Description', '')).classes('text-gray-800 whitespace-pre-wrap leading-relaxed mb-4')
                
                if project.get('Final_Deliverables'):
                    ui.label('Deliverables & Work Breakdown:').classes('font-semibold text-gray-700 mb-2')
                    ui.label(project.get('Final_Deliverables', '')).classes('text-gray-800 whitespace-pre-wrap leading-relaxed')
        
        # Project Notes Section (from main dashboard)
        with ui.card().classes('w-full p-6 mt-6'):
            ui.label('📋 Project Notes').classes('text-xl font-bold mb-4 text-blue-700')
            
            current_notes = pmbok_viewer.get_project_notes(project_id)
            
            def save_notes_from_pmbok():
                def on_notes_change(e):
                    new_notes = e.value
                    success = pmbok_viewer.update_project_notes(project_id, new_notes)
                    if success:
                        ui.notify(f'✅ Notes saved successfully', type='positive')
                        print(f"✅ Notes saved for project {project_id} from PMBOK page")
                    else:
                        ui.notify(f'❌ Failed to save notes', type='negative')
                        print(f"❌ Failed to save notes for project {project_id}")
                return on_notes_change
            
            if current_notes:
                ui.label('Current Notes:').classes('font-semibold text-gray-700 mb-2')
                ui.label(current_notes).classes('text-gray-800 mb-4 p-3 bg-gray-50 rounded border-l-4 border-blue-400 whitespace-pre-wrap')
            
            ui.label('Edit Notes:').classes('font-semibold text-gray-700 mb-2')
            
            with ui.column().classes('w-full gap-3'):
                notes_textarea_pmbok = ui.textarea(
                    label='',
                    placeholder='Add or edit project notes here...',
                    value=current_notes,
                ).classes('w-full').props('outlined rows=4')
                
                def save_notes_click_pmbok():
                    def on_save():
                        new_notes = notes_textarea_pmbok.value
                        success = pmbok_viewer.update_project_notes(project_id, new_notes)
                        if success:
                            ui.notify(f'✅ Notes saved successfully', type='positive')
                            print(f"✅ Notes saved for project {project_id} from PMBOK page")
                        else:
                            ui.notify(f'❌ Failed to save notes', type='negative')
                            print(f"❌ Failed to save notes for project {project_id}")
                    return on_save

                ui.button('💾', on_click=save_notes_click_pmbok()).classes('bg-blue-500 text-white px-4 py-2 self-start')

            ui.label('Notes are synchronized with the main project list and detail pages.').classes('text-xs text-gray-500 mt-2 italic')
        
        # Coordinator Actions Section (from main dashboard)
        with ui.card().classes('w-full p-6 mt-6'):
            ui.label('🎯 Coordinator Actions').classes('text-xl font-bold mb-4 text-blue-700')
            
            current_actions = pmbok_viewer.get_coordinator_actions(project_id)
            
            def save_actions_from_pmbok():
                def on_actions_change(e):
                    new_actions = e.value
                    success = pmbok_viewer.update_coordinator_actions(project_id, new_actions)
                    if success:
                        ui.notify(f'✅ Coordinator actions saved successfully', type='positive')
                        print(f"✅ Coordinator actions saved for project {project_id} from PMBOK page")
                    else:
                        ui.notify(f'❌ Failed to save coordinator actions', type='negative')
                        print(f"❌ Failed to save coordinator actions for project {project_id}")
                return on_actions_change
            
            if current_actions:
                ui.label('Current Action Items:').classes('font-semibold text-gray-700 mb-2')
                # Display as bulleted list
                formatted_actions = pmbok_viewer.format_actions_as_bullets(current_actions)
                ui.label(formatted_actions).classes('text-gray-800 mb-4 p-3 bg-gray-50 rounded border-l-4 border-green-400 whitespace-pre-wrap')
            
            ui.label('Edit Action Items:').classes('font-semibold text-gray-700 mb-2')
            
            with ui.column().classes('w-full gap-3'):
                actions_textarea_pmbok = ui.textarea(
                    label='',
                    placeholder='Add action items here...\nOne item per line\nThey will be displayed as bullets',
                    value=current_actions,
                ).classes('w-full').props('outlined rows=6')
                
                def save_actions_click_pmbok():
                    def on_save():
                        new_actions = actions_textarea_pmbok.value
                        success = pmbok_viewer.update_coordinator_actions(project_id, new_actions)
                        if success:
                            ui.notify(f'✅ Coordinator actions saved successfully', type='positive')
                            print(f"✅ Coordinator actions saved for project {project_id} from PMBOK page")
                        else:
                            ui.notify(f'❌ Failed to save coordinator actions', type='negative')
                            print(f"❌ Failed to save coordinator actions for project {project_id}")
                    return on_save
                
                ui.button('💾', on_click=save_actions_click_pmbok()).classes('bg-green-500 text-white px-4 py-2 self-start')
            
            ui.label('Action items are synchronized with the main project list and all detail pages.').classes('text-xs text-gray-500 mt-2 italic')


@ui.page('/pmbok-report')
def pmbok_portfolio_report():
    """Portfolio-level PMBOK report"""
    
    pmbok_viewer.refresh_data()
    metrics = pmbok_viewer.get_project_metrics()
    
    with ui.row().classes('w-full max-w-6xl mx-auto p-4 items-center'):
        ui.button('← Back to Portfolio', on_click=lambda: ui.navigate.to('/')).classes('bg-blue-500 text-white mr-4')
        ui.label('📊 PMBOK Portfolio Report').classes('text-3xl font-bold text-blue-700')
    
    with ui.column().classes('w-full max-w-6xl mx-auto p-4'):
        
        # Executive Summary
        with ui.card().classes('w-full p-6 mb-6'):
            ui.label('📈 Executive Summary').classes('text-2xl font-bold mb-4 text-blue-700')
            
            total = metrics.get('total_projects', 0)
            on_track = metrics.get('on_track_count', 0)
            at_risk = metrics.get('at_risk_count', 0)
            overdue = metrics.get('overdue_count', 0)
            
            if total > 0:
                health_percentage = (on_track / total) * 100
                ui.label(f'Portfolio Health: {health_percentage:.1f}% projects on track').classes('text-xl text-green-600 font-semibold')
            
            ui.label(f'Total Active Projects: {total}').classes('text-lg text-gray-700 mt-2')
            ui.label(f'Risk Distribution: {metrics.get("risk_distribution", {})}').classes('text-lg text-gray-700')
        
        # Process Groups Analysis
        with ui.card().classes('w-full p-6 mb-6'):
            ui.label('🔄 PMBOK Process Groups Analysis').classes('text-2xl font-bold mb-4 text-blue-700')
            
            process_dist = metrics.get('process_distribution', {})
            for process_key, count in process_dist.items():
                process_name = pmbok_viewer.process_groups.get(process_key, process_key)
                percentage = (count / total * 100) if total > 0 else 0
                ui.label(f'{process_name}: {count} projects ({percentage:.1f}%)').classes('text-lg text-gray-700 mb-2')
        
        # Risk Analysis
        with ui.card().classes('w-full p-6'):
            ui.label('⚠️ Portfolio Risk Analysis').classes('text-2xl font-bold mb-4 text-blue-700')
            
            risk_dist = metrics.get('risk_distribution', {})
            for risk_level, count in risk_dist.items():
                percentage = (count / total * 100) if total > 0 else 0
                color = 'red' if risk_level == 'High' else 'yellow' if risk_level == 'Medium' else 'green'
                ui.label(f'{risk_level} Risk: {count} projects ({percentage:.1f}%)').classes(f'text-lg text-{color}-600 mb-2 font-medium')


@ui.page('/note/{note_name}')
def view_note(note_name: str):
    """View individual Dendron note content"""
    ui.page_title(f"Note: {note_name}")
    
    # Check Dendron integration status
    dendron_status = pmbok_viewer.get_dendron_integration_status()
    
    if not dendron_status['vault_found']:
        ui.label('❌ Dendron vault not found').classes('text-red-600 text-xl')
        return
    
    # Find the note file
    notes_path = os.path.join(dendron_status['vault_path'], 'notes')
    note_file = os.path.join(notes_path, f'{note_name}.md')
    
    with ui.row().classes('w-full'):
        # Header
        with ui.card().classes('w-full'):
            ui.label(f'📄 {note_name}').classes('text-3xl font-bold text-center')
            ui.label('GSS Caribou Support Information').classes('text-lg text-center text-gray-600')
    
    # Navigation buttons
    with ui.row().classes('w-full justify-center gap-4 mb-6'):
        ui.button('← Back to GSS Support', on_click=lambda: ui.navigate.to('/dendron-integration')).classes('bg-blue-500 text-white')
        ui.button('Portfolio Overview', on_click=lambda: ui.navigate.to('/')).classes('bg-gray-500 text-white')
    
    if not os.path.exists(note_file):
        with ui.card().classes('w-full p-6 border-l-4 border-yellow-500'):
            ui.label('📝 Note Not Found').classes('text-2xl font-bold mb-4 text-yellow-700')
            ui.label(f'The note "{note_name}" does not exist yet.').classes('text-lg text-yellow-600')
            
            # If it's a project note, offer to create it
            if note_name.startswith('WLRS.LUP.CRP.caribou-portal.') and len(note_name.split('.')) == 4:
                project_id = note_name.split('.')[-1]
                project = pmbok_viewer.get_project_by_id(project_id)
                project_number = project.get('Project_Number', project_id) if project else project_id
                ui.label(f'Would you like to create a note for project {project_number}?').classes('text-sm text-gray-600 mt-2')
                
                def create_missing_note():
                    note_path = pmbok_viewer.create_dendron_project_note(project_id, dendron_status['vault_path'])
                    if note_path:
                        ui.notify(f'✅ Created note for {project_number}', type='positive')
                        ui.navigate.reload()
                    else:
                        ui.notify(f'❌ Failed to create note for {project_number}', type='negative')
                
                ui.button(f'Create Note for {project_number}', on_click=create_missing_note).classes('bg-green-500 text-white mt-3')
        return
    
    # Display note content
    with ui.card().classes('w-full p-6'):
        try:
            with open(note_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Remove YAML frontmatter if present
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    content = parts[2].strip()
            
            # Convert internal Dendron links to clickable links
            import re
            def convert_dendron_links(text):
                # Pattern for [[note.name|Display Name]] or [[note.name]]
                pattern = r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]'
                
                def replace_link(match):
                    note_ref = match.group(1)
                    display_text = match.group(2) if match.group(2) else note_ref
                    
                    # If no explicit display text, show only the part after the last dot
                    if not match.group(2) and '.' in display_text:
                        display_text = display_text.split('.')[-1]
                    
                    # Convert to our note view URL
                    if note_ref.startswith('WLRS.LUP.CRP.caribou-portal'):
                        note_url = f"/note/{note_ref}"
                        return f'[{display_text}]({note_url})'
                    else:
                        return f'**{display_text}**'  # Non-caribou notes as bold text
                
                return re.sub(pattern, replace_link, text)
            
            processed_content = convert_dendron_links(content)
            
            # Display content as markdown
            ui.markdown(processed_content).classes('prose max-w-none')
            
            # Show file info
            try:
                mtime = os.path.getmtime(note_file)
                size = os.path.getsize(note_file)
                from datetime import datetime
                last_modified = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
                size_kb = size / 1024
                
                with ui.row().classes('gap-4 mt-6 pt-4 border-t'):
                    ui.label(f'Last modified: {last_modified}').classes('text-sm text-gray-500')
                    ui.label(f'Size: {size_kb:.1f} KB').classes('text-sm text-gray-500')
            except:
                pass
                
        except Exception as e:
            ui.label(f'Error reading note: {str(e)}').classes('text-red-600')


@ui.page('/dendron-integration')
def dendron_integration():
    """GSS Caribou Support Information - Knowledge management system"""
    ui.page_title("GSS Caribou Support Information")
    
    with ui.row().classes('w-full'):
        # Header
        with ui.card().classes('w-full'):
            ui.label('� GSS Caribou Support Information').classes('text-3xl font-bold text-center')
            ui.label('Knowledge Management & Project Documentation').classes('text-lg text-center text-gray-600')
    
    # Navigation buttons
    with ui.row().classes('w-full justify-center gap-4 mb-6'):
        ui.button('Portfolio Overview', on_click=lambda: ui.navigate.to('/')).classes('bg-blue-500 text-white')
        ui.button('PMBOK Analysis', on_click=lambda: ui.navigate.to('/pmbok-report')).classes('bg-green-500 text-white')
    
    # Check Dendron integration status
    dendron_status = pmbok_viewer.get_dendron_integration_status()
    
    # Only show vault status if there's a problem
    if not dendron_status['vault_found'] or not dendron_status['can_read']:
        with ui.card().classes('w-full p-6 mb-6 border-l-4 border-red-500'):
            ui.label('⚠️ Dendron Vault Connection Issue').classes('text-2xl font-bold mb-4 text-red-700')
            
            if not dendron_status['vault_found']:
                ui.label('❌ Dendron vault not found').classes('text-lg text-red-600 font-semibold')
                ui.label('Please ensure your Dendron vault is accessible at:').classes('text-sm text-gray-600 mb-2')
                ui.label('• Set DENDRON environment variable to your vault path').classes('text-sm text-gray-500 ml-4')
                ui.label('• Or place vault in a standard location (~/Dendron, ~/dendron, etc.)').classes('text-sm text-gray-500 ml-4')
            elif not dendron_status['can_read']:
                ui.label('❌ Cannot read Dendron vault').classes('text-lg text-red-600 font-semibold')
                ui.label(f'Vault found at: {dendron_status["vault_path"]}').classes('text-sm text-gray-600')
                ui.label('Please check file permissions').classes('text-sm text-gray-600')
        return
    
    # Display main Caribou Portal note content
    main_note_path = os.path.join(dendron_status['vault_path'], 'notes', 'WLRS.LUP.CRP.caribou-portal.md')
    main_note_exists = os.path.exists(main_note_path)
    
    if main_note_exists:
        with ui.card().classes('w-full p-6 mb-6'):
            ui.label('🏠 Main Caribou Portal Documentation').classes('text-2xl font-bold mb-4 text-blue-700')
            
            try:
                # Read and display note content
                with open(main_note_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Remove YAML frontmatter if present
                if content.startswith('---'):
                    parts = content.split('---', 2)
                    if len(parts) >= 3:
                        content = parts[2].strip()
                
                # Convert internal Dendron links to clickable links
                import re
                def convert_dendron_links(text):
                    # Pattern for [[note.name|Display Name]] or [[note.name]]
                    pattern = r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]'
                    
                    def replace_link(match):
                        note_ref = match.group(1)
                        display_text = match.group(2) if match.group(2) else note_ref
                        
                        # If no explicit display text, show only the part after the last dot
                        if not match.group(2) and '.' in display_text:
                            display_text = display_text.split('.')[-1]
                        
                        # Convert to our note view URL
                        if note_ref.startswith('WLRS.LUP.CRP.caribou-portal'):
                            note_url = f"/note/{note_ref}"
                            return f'[{display_text}]({note_url})'
                        else:
                            return f'**{display_text}**'  # Non-caribou notes as bold text
                    
                    return re.sub(pattern, replace_link, text)
                
                processed_content = convert_dendron_links(content)
                
                # Display content as markdown
                ui.markdown(processed_content).classes('prose max-w-none')
                
                # Show last modified
                try:
                    mtime = os.path.getmtime(main_note_path)
                    from datetime import datetime
                    last_modified = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
                    ui.label(f'Last modified: {last_modified}').classes('text-sm text-gray-500 mt-4')
                except:
                    pass
                    
            except Exception as e:
                ui.label(f'Error reading main note: {str(e)}').classes('text-red-600')
                
        # Update button for main note
        with ui.row().classes('w-full justify-center mb-6'):
            def update_main_note():
                note_path = pmbok_viewer.create_main_caribou_portal_note(dendron_status['vault_path'])
                if note_path:
                    ui.notify('✅ Updated main Caribou Portal note', type='positive')
                    ui.navigate.reload()
                else:
                    ui.notify('❌ Failed to update main note', type='negative')
            
            ui.button('🔄 Update Main Note', on_click=update_main_note).classes('bg-blue-500 text-white')
    
    else:
        # Main note doesn't exist - show creation option
        with ui.card().classes('w-full p-6 mb-6'):
            ui.label('🏠 Main Caribou Portal Note').classes('text-2xl font-bold mb-4 text-blue-700')
            ui.label('📝 Main note not found').classes('text-lg text-yellow-600 font-semibold mb-2')
            ui.label('Create the main WLRS.LUP.CRP.caribou-portal note to start organizing your project notes').classes('text-sm text-gray-600 mb-3')
            
            def create_main_note():
                note_path = pmbok_viewer.create_main_caribou_portal_note(dendron_status['vault_path'])
                if note_path:
                    ui.notify('✅ Created main Caribou Portal note', type='positive')
                    ui.navigate.reload()  # Reload page to update display
                else:
                    ui.notify('❌ Failed to create main note', type='negative')
            
            ui.button('Create Main Note', on_click=create_main_note).classes('bg-green-500 text-white')
    
    # Search for existing WLRS.LUP.CRP.caribou-portal notes
    notes_path = os.path.join(dendron_status['vault_path'], 'notes')
    caribou_notes = []
    
    try:
        pattern = os.path.join(notes_path, 'WLRS.LUP.CRP.caribou-portal*.md')
        caribou_files = glob.glob(pattern)
        
        for file_path in caribou_files:
            try:
                filename = os.path.basename(file_path)
                note_name = filename.replace('.md', '')
                mtime = os.path.getmtime(file_path)
                from datetime import datetime
                last_modified = datetime.fromtimestamp(mtime)
                
                caribou_notes.append({
                    'name': note_name,
                    'path': file_path,
                    'filename': filename,
                    'modified': last_modified
                })
            except:
                continue
        
        # Sort by modification time (newest first)
        caribou_notes.sort(key=lambda x: x['modified'], reverse=True)
    except Exception as e:
        ui.notify(f'Error scanning notes: {str(e)}', type='warning')
    
    # Project note creation tools
    with ui.card().classes('w-full p-6'):
        ui.label('� Create Project Notes').classes('text-2xl font-bold mb-4 text-blue-700')
        ui.label('Create individual project notes following the WLRS.LUP.CRP.caribou-portal.PROJECT_ID pattern').classes('text-sm text-gray-600 mb-4')
        
        # Project selector
        project_options = {p.get('Project_ID', 'N/A'): f"{p.get('Project_ID', 'N/A')}: {p.get('Project_Name', 'Unnamed Project')}" 
                         for p in pmbok_viewer.projects}
        
        with ui.row().classes('w-full items-center gap-4'):
            selected_project = ui.select(
                label="Select Project for Note Creation",
                options=project_options,
                value=None
            ).classes('flex-grow')
            
            def create_project_note():
                if selected_project.value:
                    note_path = pmbok_viewer.create_dendron_project_note(selected_project.value, dendron_status['vault_path'])
                    if note_path:
                        filename = os.path.basename(note_path)
                        ui.notify(f'✅ Created: {filename}', type='positive')
                        ui.navigate.reload()  # Reload to show new note
                    else:
                        ui.notify('❌ Failed to create note', type='negative')
                else:
                    ui.notify('Please select a project first', type='warning')
            
            ui.button('Create Project Note', on_click=create_project_note).classes('bg-green-500 text-white')
        
        # Quick create buttons for active projects
        active_projects = [p for p in pmbok_viewer.projects if pmbok_viewer.get_project_effective_status(p).lower() in ['in progress', 'active']]
        if active_projects:
            ui.label('Quick create notes for active projects:').classes('text-sm font-semibold mt-4 mb-2')
            with ui.row().classes('gap-2 flex-wrap'):
                for project in active_projects[:6]:  # Show first 6 active projects
                    project_id = project.get('Project_ID', '')
                    project_name = project.get('Project_Name', 'Unnamed')[:20]
                    project_number = project.get('Project_Number', 'N/A')
                    
                    def create_quick_note(pid=project_id, pname=project_name, pnumber=project_number):
                        note_path = pmbok_viewer.create_dendron_project_note(pid, dendron_status['vault_path'])
                        if note_path:
                            ui.notify(f'✅ Created note for {pnumber}', type='positive')
                            ui.navigate.reload()
                        else:
                            ui.notify(f'❌ Failed to create note for {pnumber}', type='negative')
                    
                    ui.button(f'{project_number}: {project_name}', on_click=create_quick_note).classes('bg-blue-400 text-white text-xs')



# @ui.page('/engagement')
# def engagement_page():
#     """Team engagement analysis page"""
#     ui.page_title("Team Engagement Analysis")
    
#     # Header
#     with ui.row().classes('w-full'):
#         with ui.card().classes('w-full'):
#             ui.label('👥 Team Engagement Analysis').classes('text-3xl font-bold text-center')
#             ui.label('CRP/Caribou Project Resource Allocation Summary').classes('text-lg text-center text-gray-600')
    
#     # Navigation buttons
#     with ui.row().classes('w-full justify-center gap-4 mb-6'):
#         ui.button('Portfolio Overview', on_click=lambda: ui.navigate.to('/')).classes('bg-blue-500 text-white')
#         ui.button('Status Dashboard', on_click=lambda: ui.navigate.to('/status-dashboard')).classes('bg-purple-500 text-white')
#         ui.button('PMBOK Analysis', on_click=lambda: ui.navigate.to('/pmbok-report')).classes('bg-green-500 text-white')
    
#     # Configuration validation
#     try:
#         from enhanced_get_team_engagement import TeamEngagementAnalyzer
#         analyzer = TeamEngagementAnalyzer()
#         config = analyzer.validate_configuration()
        
#         if not config['is_valid']:
#             with ui.card().classes('w-full bg-yellow-50'):
#                 ui.label('⚠️ Configuration Required').classes('text-xl font-bold text-yellow-600')
#                 ui.label('Missing environment variables:').classes('text-yellow-700')
#                 for var in config['missing_vars']:
#                     ui.label(f'• {var}').classes('text-yellow-600 ml-4')
#                 ui.label('Please check your .env file configuration.').classes('text-gray-600 mt-2')
#                 ui.label('This feature requires ArcGIS Online access to analyze all CRP/Caribou projects.').classes('text-gray-600')
#             return
        
#         if not config['client_available']:
#             with ui.card().classes('w-full bg-red-50'):
#                 ui.label('❌ ArcGIS Connection Failed').classes('text-xl font-bold text-red-600')
#                 ui.label('Could not connect to ArcGIS Online.').classes('text-red-500')
#                 ui.label('Please check your credentials and network connection.').classes('text-gray-600')
#             return
    
#     except ImportError as e:
#         with ui.card().classes('w-full bg-red-50'):
#             ui.label('❌ Module Import Error').classes('text-xl font-bold text-red-600')
#             ui.label(f'Could not import team engagement analyzer: {e}').classes('text-red-500')
#             ui.label('Please ensure enhanced_get_team_engagement.py is available.').classes('text-gray-600')
#         return
    
#     # Loading indicator
#     loading_container = ui.row().classes('w-full justify-center')
#     with loading_container:
#         ui.spinner('dots', size='lg', color='primary')
#         ui.label('Loading engagement data from ArcGIS...').classes('text-lg ml-4')
    
#     # Analyze engagement data
#     try:
#         print("Starting engagement analysis...")
#         analysis_result = analyzer.analyze_engagement_data()
        
#         # Clear loading indicator
#         loading_container.clear()
        
#         if analysis_result['error']:
#             with ui.card().classes('w-full bg-red-50'):
#                 ui.label('❌ Error Loading Data').classes('text-xl font-bold text-red-600')
#                 ui.label(f'Error: {analysis_result["error"]}').classes('text-red-500')
#                 ui.label('Please check your ArcGIS configuration and try again.').classes('text-gray-600')
                
#                 # Show debugging information
#                 ui.label('Debugging Information:').classes('text-sm font-semibold text-gray-700 mt-4')
#                 ui.label(f'GSS_PROJECTS_TABLE_URL: {os.getenv("GSS_PROJECTS_TABLE_URL", "Not set")[:100]}...').classes('text-xs text-gray-600')
#                 ui.label(f'GSS_RESOURCES_TABLE_URL: {os.getenv("GSS_RESOURCES_TABLE_URL", "Not set")[:100]}...').classes('text-xs text-gray-600')
#                 ui.label(f'ARCGIS_USERNAME: {"Set" if os.getenv("ARCGIS_USERNAME") else "Not set"}').classes('text-xs text-gray-600')
#             return
        
#         engagement_data = analysis_result['engagement_summary']
#         total_projects = analysis_result['total_projects']
#         total_people = analysis_result['total_people']
        
#         # Show results
#         with ui.row().classes('w-full'):
#             with ui.column().classes('w-full'):
                
#                 # Summary metrics
#                 with ui.row().classes('w-full justify-center gap-4 mb-6'):
#                     with ui.card().classes('text-center bg-blue-50 p-4'):
#                         ui.label(str(total_projects)).classes('text-3xl font-bold text-blue-600')
#                         ui.label('Total CRP/Caribou Projects').classes('text-gray-600')
                    
#                     with ui.card().classes('text-center bg-green-50 p-4'):
#                         ui.label(str(total_people)).classes('text-3xl font-bold text-green-600')
#                         ui.label('People Engaged').classes('text-gray-600')
                    
#                     if total_people > 0:
#                         avg_projects = round(total_projects / total_people, 1)
#                         with ui.card().classes('text-center bg-orange-50 p-4'):
#                             ui.label(str(avg_projects)).classes('text-3xl font-bold text-orange-600')
#                             ui.label('Avg Projects per Person').classes('text-gray-600')
                
#                 # Show detailed analysis breakdown
#                 with ui.card().classes('w-full mb-6 p-4 bg-blue-50 border-l-4 border-blue-400'):
#                     ui.label('📊 Analysis Breakdown').classes('text-lg font-bold text-blue-800 mb-3')
                    
#                     # Calculate detailed statistics
#                     actual_workers = {}
#                     coordinator_fallbacks = {}
#                     explicit_assignments = 0
#                     coordinator_assignments = 0
                    
#                     for person, data in engagement_data.items():
#                         has_actual_role = any(role != 'Coordinator (default)' for role in data.get('roles', []))
#                         if has_actual_role:
#                             actual_workers[person] = data
#                         else:
#                             coordinator_fallbacks[person] = data
                        
#                         # Count assignment types
#                         for project in data.get('projects', []):
#                             if project.get('role') == 'Coordinator (default)':
#                                 coordinator_assignments += 1
#                             else:
#                                 explicit_assignments += 1
                    
#                     projects_with_assignments = len(set(project.get('project_id') for person_data in engagement_data.values() 
#                                                       for project in person_data.get('projects', []) 
#                                                       if project.get('role') != 'Coordinator (default)'))
                    
#                     with ui.grid(columns=2).classes('gap-4 w-full'):
#                         with ui.column():
#                             ui.label(f'• {total_projects} CRP/Caribou projects found (current and completed)').classes('text-sm text-blue-700')
#                             ui.label(f'• {projects_with_assignments} projects with explicit team assignments').classes('text-sm text-blue-700')
#                             ui.label(f'• {len(actual_workers)} people with assigned work roles').classes('text-sm text-blue-700')
                        
#                         with ui.column():
#                             ui.label(f'• {explicit_assignments} actual resource assignments found').classes('text-sm text-blue-700')
#                             ui.label(f'• {coordinator_assignments} projects using coordinator fallback').classes('text-sm text-blue-700')
#                             ui.label(f'• {total_people} total people engaged across all projects').classes('text-sm text-blue-700')
                
#                 # Top engaged people (separated by assignment type)
#                 if engagement_data:
#                     # Show actual team members first
#                     if actual_workers:
#                         ui.label('🏆 Most Engaged Team Members (Assigned Roles)').classes('text-2xl font-bold mb-4')
#                         actual_top_people = sorted(actual_workers.items(), key=lambda x: x[1]['total_projects'], reverse=True)[:5]
                        
#                         with ui.card().classes('w-full mb-6'):
#                             for i, (person_name, person_data) in enumerate(actual_top_people, 1):
#                                 actual_projects = len([p for p in person_data['projects'] if p.get('role') != 'Coordinator (default)'])
#                                 actual_roles = [r for r in person_data['roles'] if r != 'Coordinator (default)']
#                                 roles = ', '.join(actual_roles)
                                
#                                 # Color coding for workload levels
#                                 if actual_projects >= 5:
#                                     color_class = 'text-red-600'
#                                     icon = '🔥'
#                                 elif actual_projects >= 3:
#                                     color_class = 'text-orange-600'
#                                     icon = '⚡'
#                                 else:
#                                     color_class = 'text-green-600'
#                                     icon = '✅'
                                
#                                 with ui.row().classes('items-center gap-4 p-2 border-b'):
#                                     ui.label(f'{i}.').classes('text-lg font-bold w-8')
#                                     ui.label(icon).classes('text-xl')
#                                     ui.label(person_name).classes('text-lg font-semibold flex-grow')
#                                     ui.label(f'{actual_projects} projects').classes(f'text-lg {color_class} font-bold')
#                                     ui.label(f'({roles})').classes('text-sm text-gray-500')
                    
#                     # Show coordinator fallbacks if there are significant numbers
#                     if coordinator_fallbacks and len(coordinator_fallbacks) > 3:
#                         ui.label('📋 Top Project Coordinators (Fallback Assignment)').classes('text-xl font-bold mb-4 mt-6')
#                         ui.label('These are coordinators for projects without explicit team assignments.').classes('text-sm text-gray-600 mb-4')
                        
#                         coordinator_top_people = sorted(coordinator_fallbacks.items(), key=lambda x: x[1]['total_projects'], reverse=True)[:5]
                        
#                         with ui.card().classes('w-full mb-6 bg-yellow-50'):
#                             for i, (person_name, person_data) in enumerate(coordinator_top_people, 1):
#                                 total_projects = person_data['total_projects']
                                
#                                 with ui.row().classes('items-center gap-4 p-2 border-b border-yellow-200'):
#                                     ui.label(f'{i}.').classes('text-lg font-bold w-8')
#                                     ui.label('📋').classes('text-xl')
#                                     ui.label(person_name).classes('text-lg font-semibold flex-grow')
#                                     ui.label(f'{total_projects} projects').classes('text-lg text-orange-600 font-bold')
#                                     ui.label('(Coordinator)').classes('text-sm text-gray-500')
                
#                 # Engagement table
#                 if engagement_data:
#                     ui.label('📊 Complete Engagement Summary').classes('text-2xl font-bold mb-4 mt-8')
                    
#                     # Sort people by total projects (descending)
#                     sorted_people = sorted(engagement_data.items(), 
#                                          key=lambda x: x[1]['total_projects'], 
#                                          reverse=True)
                    
#                     with ui.card().classes('w-full'):
#                         with ui.element('div').classes('overflow-x-auto'):
#                             with ui.element('table').classes('min-w-full divide-y divide-gray-200'):
#                                 # Header
#                                 with ui.element('thead').classes('bg-gray-50'):
#                                     with ui.element('tr'):
#                                         ui.element('th').classes('px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider').add('Person')
#                                         ui.element('th').classes('px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider').add('Total Projects')
#                                         ui.element('th').classes('px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider').add('As Coordinator')
#                                         ui.element('th').classes('px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider').add('As Team Member')
#                                         ui.element('th').classes('px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider').add('Roles')
#                                         ui.element('th').classes('px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider').add('Projects')
                                
#                                 # Body
#                                 with ui.element('tbody').classes('bg-white divide-y divide-gray-200'):
#                                     for person_name, person_data in sorted_people:
#                                         total_projects = person_data['total_projects']
#                                         coord_projects = person_data['coordinator_projects']
#                                         team_projects = person_data['team_member_projects']
#                                         roles = ', '.join(person_data['roles'])
                                        
#                                         # Color coding based on workload
#                                         if total_projects >= 5:
#                                             row_class = 'bg-red-50'
#                                         elif total_projects >= 3:
#                                             row_class = 'bg-yellow-50'
#                                         else:
#                                             row_class = 'bg-white'
                                        
#                                         with ui.element('tr').classes(row_class):
#                                             with ui.element('td').classes('px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900'):
#                                                 ui.label(person_name)
                                            
#                                             with ui.element('td').classes('px-6 py-4 whitespace-nowrap text-sm text-gray-500'):
#                                                 ui.label(str(total_projects)).classes('font-semibold')
                                            
#                                             with ui.element('td').classes('px-6 py-4 whitespace-nowrap text-sm text-gray-500'):
#                                                 ui.label(str(coord_projects))
                                            
#                                             with ui.element('td').classes('px-6 py-4 whitespace-nowrap text-sm text-gray-500'):
#                                                 ui.label(str(team_projects))
                                            
#                                             with ui.element('td').classes('px-6 py-4 whitespace-nowrap text-sm text-gray-500'):
#                                                 ui.label(roles)
                                            
#                                             with ui.element('td').classes('px-6 py-4 whitespace-nowrap text-sm text-gray-500'):
#                                                 # Show project list (truncated)
#                                                 project_list = []
#                                                 for proj in person_data['projects'][:3]:  # Show first 3
#                                                     project_list.append(f"{proj['project_number']} ({proj['role']})")
                                                
#                                                 display_text = ', '.join(project_list)
#                                                 if len(person_data['projects']) > 3:
#                                                     display_text += f" +{len(person_data['projects']) - 3} more"
                                                
#                                                 ui.label(display_text)
#                 else:
#                     with ui.card().classes('w-full bg-gray-50'):
#                         ui.label('No engagement data found').classes('text-lg text-gray-600')
#                         ui.label(f'Found {total_projects} projects but no resource assignments').classes('text-gray-500')
                
#                 # Analytics section
#                 if engagement_data:
#                     # Client engagement analysis
#                     ui.label('👥 Client Engagement Analysis').classes('text-2xl font-bold mb-4 mt-8')
                    
#                     try:
#                         # Get client engagement data
#                         client_result = analyzer.analyze_client_engagement()
                        
#                         if client_result.get('error'):
#                             with ui.card().classes('w-full bg-red-50'):
#                                 ui.label('Error loading client data').classes('text-lg text-red-600')
#                                 ui.label(client_result['error']).classes('text-red-500')
#                         else:
#                             client_data = client_result.get('client_summary', {})
#                             total_clients = client_result.get('total_clients', 0)
                            
#                             with ui.card().classes('w-full mb-6'):
#                                 ui.label(f'📊 Client Summary: {total_clients} clients have submitted {total_projects} CRP/Caribou projects').classes('text-lg font-semibold mb-4')
                                
#                                 if client_data:
#                                     # Top clients table
#                                     top_clients = analyzer.get_top_clients(client_data, 10)
                                    
#                                     with ui.element('div').classes('overflow-x-auto'):
#                                         with ui.element('table').classes('min-w-full divide-y divide-gray-200'):
#                                             # Header
#                                             with ui.element('thead').classes('bg-gray-50'):
#                                                 with ui.element('tr'):
#                                                     ui.element('th').classes('px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider').add('Client Name')
#                                                     ui.element('th').classes('px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider').add('Total Projects')
#                                                     ui.element('th').classes('px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider').add('Status Breakdown')
#                                                     ui.element('th').classes('px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider').add('Recent Projects')
                                            
#                                             # Body
#                                             with ui.element('tbody').classes('bg-white divide-y divide-gray-200'):
#                                                 for client_name, client_data_item in top_clients:
#                                                     total_projects = client_data_item['total_projects']
                                                    
#                                                     # Color coding based on project count
#                                                     if total_projects >= 8:
#                                                         row_class = 'bg-green-50'
#                                                     elif total_projects >= 5:
#                                                         row_class = 'bg-blue-50'
#                                                     elif total_projects >= 3:
#                                                         row_class = 'bg-yellow-50'
#                                                     else:
#                                                         row_class = 'bg-white'
                                                    
#                                                     with ui.element('tr').classes(row_class):
#                                                         with ui.element('td').classes('px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900'):
#                                                             ui.label(client_name)
                                                        
#                                                         with ui.element('td').classes('px-6 py-4 whitespace-nowrap text-sm text-gray-500'):
#                                                             ui.label(str(total_projects)).classes('font-semibold')
                                                        
#                                                         with ui.element('td').classes('px-6 py-4 whitespace-nowrap text-sm text-gray-500'):
#                                                             # Status breakdown
#                                                             statuses = client_data_item.get('project_statuses', {})
#                                                             status_parts = []
#                                                             for status, count in statuses.items():
#                                                                 status_parts.append(f"{status}: {count}")
#                                                             ui.label(', '.join(status_parts))
                                                        
#                                                         with ui.element('td').classes('px-6 py-4 whitespace-nowrap text-sm text-gray-500'):
#                                                             # Recent projects (show first 3)
#                                                             projects = client_data_item.get('projects', [])
#                                                             recent_projects = []
#                                                             for proj in projects[:3]:
#                                                                 recent_projects.append(f"{proj.get('number', 'N/A')}")
                                                            
#                                                             display_text = ', '.join(recent_projects)
#                                                             if len(projects) > 3:
#                                                                 display_text += f" +{len(projects) - 3} more"
                                                            
#                                                             ui.label(display_text)
                    
#                     except Exception as e:
#                         with ui.card().classes('w-full bg-red-50'):
#                             ui.label('Error loading client analysis').classes('text-lg text-red-600')
#                             ui.label(str(e)).classes('text-red-500')
                    
#                     # Workload distribution
#                     ui.label('📈 Workload Distribution').classes('text-2xl font-bold mb-4 mt-8')
#                     workload_counts = analyzer.get_workload_distribution(engagement_data)
                    
#                     with ui.card().classes('w-full'):
#                         ui.label('People by Project Count').classes('text-lg font-semibold mb-4')
                        
#                         for category in ['1 project', '2 projects', '3 projects', '4 projects', '5+ projects']:
#                             count = workload_counts.get(category, 0)
#                             if count > 0:
#                                 with ui.row().classes('items-center gap-4 mb-2'):
#                                     ui.label(category).classes('w-24')
                                    
#                                     # Simple bar chart
#                                     max_width = max(workload_counts.values()) if workload_counts else 1
#                                     bar_width = (count / max_width) * 200  # Max 200px wide
                                    
#                                     with ui.element('div').classes(f'bg-blue-500 h-6 rounded').style(f'width: {bar_width}px'):
#                                         pass
                                    
#                                     ui.label(f'{count} people').classes('ml-2')
                    
#                     # Role distribution
#                     ui.label('🎭 Role Distribution').classes('text-2xl font-bold mb-4 mt-8')
#                     role_stats = analyzer.get_role_distribution(engagement_data)
                    
#                     with ui.card().classes('w-full'):
#                         with ui.row().classes('justify-center gap-8'):
#                             for role, count in role_stats.items():
#                                 if count > 0:
#                                     with ui.card().classes('text-center bg-gray-50 p-4'):
#                                         ui.label(str(count)).classes('text-2xl font-bold text-blue-600')
#                                         ui.label(f'{role} Only' if role != 'Both' else 'Both Roles').classes('text-gray-600')
                
#                 # Action buttons
#                 with ui.row().classes('w-full justify-center mt-8 gap-4'):
#                     def refresh_engagement():
#                         ui.navigate.reload()
                    
#                     def test_analyzer():
#                         # Run the standalone test
#                         from enhanced_get_team_engagement import main as test_main
#                         test_main()
#                         ui.notify('Test completed! Check terminal output.', type='positive')
                    
#                     ui.button('🔄 Refresh Data', on_click=refresh_engagement).classes('bg-blue-500 text-white px-6 py-3')
#                     ui.button('🧪 Test Analyzer', on_click=test_analyzer).classes('bg-gray-500 text-white px-6 py-3')
        
#     except Exception as e:
#         loading_container.clear()
#         with ui.card().classes('w-full bg-red-50'):
#             ui.label('❌ Error Loading Engagement Data').classes('text-xl font-bold text-red-600')
#             ui.label(f'Error: {str(e)}').classes('text-red-500')
#             ui.label('Please check your ArcGIS configuration and try again.').classes('text-gray-600')
            
#             # Show more debugging info
#             import traceback
#             ui.label('Technical Details:').classes('text-sm font-semibold text-gray-700 mt-4')
#             with ui.element('pre').classes('text-xs text-gray-600 bg-gray-100 p-2 rounded overflow-auto max-h-40'):
#                 ui.label(traceback.format_exc())


if __name__ in {"__main__", "__mp_main__"}:
    print("🚀 Starting PMBOK-Aligned Caribou Portal...")
    print("📊 Loading project portfolio...")
    
    # if not os.path.exists(json_file_path):
    #     print("❌ JSON file not found. Please run enhanced_get_projects_s3.py first.")
    #     exit(1)
    
    count = pmbok_viewer.refresh_data()
    metrics = pmbok_viewer.get_project_metrics()
    
    print(f"✅ Portfolio loaded: {count} projects")
    print(f"📈 Health: {metrics.get('on_track_count', 0)} on track, {metrics.get('at_risk_count', 0)} at risk, {metrics.get('overdue_count', 0)} overdue")
    print("🌐 Starting PMBOK dashboard...")
    print("📱 Portfolio Dashboard: http://localhost:8080")
    print("📊 PMBOK Report: http://localhost:8080/pmbok-report")
    print("🔍 Project Analysis: http://localhost:8080/pmbok/{project_id}")
    print("� GSS Caribou Support Information: http://localhost:8080/dendron-integration")
    
    ui.run(
        host='0.0.0.0',
        port=8080,
        title='PMBOK Caribou Portal - Project Portfolio Management',
        reload=True,
        show=False
    )
