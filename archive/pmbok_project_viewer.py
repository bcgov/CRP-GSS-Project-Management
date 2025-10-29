#!/usr/bin/env python3
"""
PMBOK-Aligned Project Management Dashboard for Caribou Portal
Implements PMI PMBOK 7th Edition standards with 10 Knowledge Areas and 5 Process Groups
"""

import json
import os
import yaml
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from nicegui import ui

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("python-dotenv not installed, using os.environ directly")


class PMBOKProjectViewer:
    """PMI PMBOK-aligned project management viewer"""
    
    def __init__(self, json_file_path: str):
        self.json_file_path = json_file_path
        self.status_overrides_file = '/home/cfolkers/caribou_portal/project_status_overrides.json'
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
        if not os.path.exists(self.json_file_path):
            return []
        
        try:
            with open(self.json_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
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
        try:
            with open(self.status_overrides_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            # Create empty overrides file if it doesn't exist
            return {}
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in {self.status_overrides_file}")
            return {}
    
    def save_status_overrides(self):
        """Save status overrides to JSON file"""
        try:
            with open(self.status_overrides_file, 'w') as f:
                json.dump(self.status_overrides, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving status overrides: {e}")
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
        self.status_overrides[str(project_id)] = {
            'status': new_status,
            'updated_by': updated_by,
            'updated_at': datetime.now().isoformat(),
            'original_status': next((p.get('Project_Status', 'Unknown') for p in self.projects if str(p.get('Project_ID', '')) == str(project_id)), 'Unknown')
        }
        return self.save_status_overrides()
    
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
{yaml.dump(frontmatter, default_flow_style=False).strip()}
---

# Caribou Portal - PMBOK Project Management System

> **PMBOK 7th Edition Aligned Dashboard**  
> PMI Project Management Body of Knowledge implementation for portfolio management

## 🚀 Quick Access
- 🌐 [Portfolio Dashboard](http://localhost:8080)
- 📊 [PMBOK Analysis Report](http://localhost:8080/pmbok-report)
- 📋 [Status Dashboard](http://localhost:8080/status-dashboard)
- 🌿 [Dendron Integration](http://localhost:8080/dendron-integration)

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
{yaml.dump(frontmatter, default_flow_style=False).strip()}
---

# Caribou Portal - Project {project_id}: {project_name}

> Part of the [[WLRS.LUP.CRP.caribou-portal]] PMBOK project management system

## Quick Links
- 🌐 [PMBOK Portal Project View](http://localhost:8080/pmbok/{project_id})
- 📊 [Project Dashboard](http://localhost:8080)
- 🌿 [Dendron Integration](http://localhost:8080/dendron-integration)

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


# Initialize PMBOK-aligned project viewer
json_file_path = "/home/cfolkers/caribou_portal/projects_for_Cole_Folkers.json"
pmbok_viewer = PMBOKProjectViewer(json_file_path)


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
                            
                            with ui.row().classes('items-center gap-2 mt-1'):
                                ui.label(f"#{project_id}:").classes('text-xs font-mono text-gray-500')
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
                        ui.label(f"#{project_id}: {project_name}").classes('text-lg font-bold')
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
    current_status = pmbok_viewer.get_project_effective_status(project)
    original_status = project.get('Project_Status', 'Unknown')
    
    ui.page_title(f"Edit Status - {project_name}")
    
    with ui.card().classes('w-full max-w-2xl mx-auto'):
        with ui.card_section():
            ui.label(f"Edit Status for Project #{project_id}").classes('text-2xl font-bold')
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
    projects_container = ui.column().classes('w-full max-w-7xl mx-auto')
    
    def update_dashboard():
        """Update dashboard with latest PMBOK metrics"""
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
            
            with ui.card().classes('p-4 bg-green-50'):
                ui.label(f'✅ On Track: {metrics.get("on_track_count", 0)}').classes('text-lg font-semibold text-green-700')
            
            with ui.card().classes('p-4 bg-yellow-50'):
                ui.label(f'⚠️ At Risk: {metrics.get("at_risk_count", 0)}').classes('text-lg font-semibold text-yellow-700')
            
            with ui.card().classes('p-4 bg-red-50'):
                ui.label(f'🚨 Overdue: {metrics.get("overdue_count", 0)}').classes('text-lg font-semibold text-red-700')
        
        # PMBOK Process Groups
        with process_container:
            ui.label('PMBOK Process Groups Distribution:').classes('text-xl font-bold text-gray-700 w-full text-center mb-2')
            
            process_dist = metrics.get('process_distribution', {})
            for process_key, count in process_dist.items():
                if count > 0:
                    process_name = pmbok_viewer.process_groups.get(process_key, process_key)
                    with ui.card().classes('p-3 bg-gray-50'):
                        ui.label(f'{process_name}: {count}').classes('text-sm font-medium text-gray-700')
        
        # Project cards
        display_pmbok_projects()
        ui.notify(f'✅ PMBOK Dashboard updated! Portfolio: {count} projects', type='positive')
    
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
                ui.button('🌿 Dendron Notes', on_click=lambda: ui.navigate.to('/dendron-integration')).classes('bg-indigo-500 text-white px-6 py-2')
            
            # Project grid with PMBOK metrics (sorted by due date)
            sorted_projects = pmbok_viewer.sort_projects_by_due_date(pmbok_viewer.projects)
            
            # Add sorting indicator
            ui.label('Projects sorted by due date (nearest deadlines first)').classes('text-sm text-gray-600 text-center w-full mb-2')
            
            with ui.row().classes('w-full gap-4 flex-wrap justify-center'):
                for project in sorted_projects:
                    create_pmbok_project_card(project)
    
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
                ui.label('• Cole Folkers (Project Manager/Coordinator)').classes('text-gray-900 ml-4')
                
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
            ui.label(project.get('Project_Name', 'N/A')).classes('text-2xl font-bold text-blue-700 mb-4')
            
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
                ui.label('• Cole Folkers (Project Manager/Coordinator)').classes('text-gray-900 ml-4')
                
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


@ui.page('/dendron-integration')
def dendron_integration():
    """Dendron vault integration page"""
    ui.page_title("Dendron Integration")
    
    with ui.row().classes('w-full'):
        # Header
        with ui.card().classes('w-full'):
            ui.label('🌿 Dendron Vault Integration').classes('text-3xl font-bold text-center')
            ui.label('Connect your VS Code Dendron notes with project data').classes('text-lg text-center text-gray-600')
    
    # Navigation buttons
    with ui.row().classes('w-full justify-center gap-4 mb-6'):
        ui.button('Portfolio Overview', on_click=lambda: ui.navigate.to('/')).classes('bg-blue-500 text-white')
        ui.button('PMBOK Analysis', on_click=lambda: ui.navigate.to('/pmbok-report')).classes('bg-green-500 text-white')
    
    # Check Dendron integration status
    dendron_status = pmbok_viewer.get_dendron_integration_status()
    
    # Status display
    with ui.card().classes('w-full p-6 mb-6'):
        ui.label('📋 Dendron Vault Status').classes('text-2xl font-bold mb-4 text-blue-700')
        
        if dendron_status['vault_found']:
            ui.label('✅ Dendron vault found!').classes('text-lg text-green-600 font-semibold')
            ui.label(f'📁 Vault path: {dendron_status["vault_path"]}').classes('text-sm text-gray-600 mb-2')
            ui.label(f'📄 Total notes: {dendron_status["note_count"]}').classes('text-sm text-gray-600')
            ui.label(f'📊 Project notes: {dendron_status["project_notes"]}').classes('text-sm text-gray-600')
            
            permissions = []
            if dendron_status['can_read']:
                permissions.append('✅ Read')
            else:
                permissions.append('❌ Read')
            if dendron_status['can_write']:
                permissions.append('✅ Write')
            else:
                permissions.append('❌ Write')
            
            ui.label(f'🔐 Permissions: {" | ".join(permissions)}').classes('text-sm text-gray-600')
        else:
            ui.label('❌ Dendron vault not found').classes('text-lg text-red-600 font-semibold')
            ui.label('Please ensure your Dendron vault is in a standard location:').classes('text-sm text-gray-600 mb-2')
            
            vault_locations = [
                '~/Dendron', '~/dendron', '~/Documents/Dendron', 
                '~/Documents/dendron', '~/notes', '~/Notes'
            ]
            for location in vault_locations:
                ui.label(f'• {location}').classes('text-sm text-gray-500 ml-4')
    
    if dendron_status['vault_found']:
        # Main note management
        with ui.card().classes('w-full p-6 mb-6'):
            ui.label('🏠 Main Note Management').classes('text-2xl font-bold mb-4 text-blue-700')
            ui.label('Structure: WLRS.LUP.CRP.caribou-portal → WLRS.LUP.CRP.caribou-portal.PROJECT_ID').classes('text-sm text-gray-600 mb-4')
            
            with ui.row().classes('w-full items-center gap-4'):
                ui.label('Main Hub Note:').classes('text-lg font-semibold')
                
                def create_main_note():
                    note_path = pmbok_viewer.create_main_caribou_portal_note(dendron_status['vault_path'])
                    if note_path:
                        ui.notify(f'✅ Created/updated main note: WLRS.LUP.CRP.caribou-portal.md', type='positive')
                    else:
                        ui.notify('❌ Failed to create main note', type='negative')
                
                ui.button('Create Main Caribou Portal Note', on_click=create_main_note).classes('bg-blue-500 text-white')
        
        # Project integration tools
        with ui.card().classes('w-full p-6 mb-6'):
            ui.label('🔗 Project Integration Tools').classes('text-2xl font-bold mb-4 text-blue-700')
            
            # Environment variable info
            dendron_env = os.getenv('DENDRON')
            if dendron_env:
                ui.label(f'📁 Using DENDRON environment variable: {dendron_env}').classes('text-sm text-green-600 mb-2')
            else:
                ui.label('⚠️ No DENDRON environment variable set, using auto-detected path').classes('text-sm text-yellow-600 mb-2')
            
            # Project selector for note creation
            with ui.row().classes('w-full items-center gap-4 mb-4'):
                project_options = {p.get('Project_ID', 'N/A'): f"{p.get('Project_ID', 'N/A')}: {p.get('Project_Name', 'Unnamed Project')}" 
                                 for p in pmbok_viewer.projects}
                
                selected_project = ui.select(
                    label="Select Project for Note Creation",
                    options=project_options,
                    value=None
                ).classes('flex-grow')
                
                def create_project_note():
                    if selected_project.value:
                        note_path = pmbok_viewer.create_dendron_project_note(selected_project.value, dendron_status['vault_path'])
                        if note_path:
                            ui.notify(f'✅ Created note: {os.path.basename(note_path)}', type='positive')
                        else:
                            ui.notify('❌ Failed to create note', type='negative')
                
                ui.button('Create Project Note', on_click=create_project_note).classes('bg-green-500 text-white')
        
        # Existing project notes
        with ui.card().classes('w-full p-6'):
            ui.label('📝 Existing Project Notes').classes('text-2xl font-bold mb-4 text-blue-700')
            
            # Search for existing project notes for each project
            with ui.grid(columns=2).classes('w-full gap-4'):
                for project in pmbok_viewer.projects[:6]:  # Show first 6 projects
                    project_id = project.get('Project_ID', 'N/A')
                    project_name = project.get('Project_Name', 'Unnamed Project')
                    
                    with ui.card().classes('p-4'):
                        ui.label(f'Project {project_id}').classes('text-lg font-bold text-blue-600')
                        ui.label(project_name[:50] + ('...' if len(project_name) > 50 else '')).classes('text-sm text-gray-600 mb-2')
                        
                        # Find related notes
                        related_notes = pmbok_viewer.find_project_notes_in_dendron(project_id, dendron_status['vault_path'])
                        
                        if related_notes:
                            ui.label(f'📄 {len(related_notes)} related notes found:').classes('text-sm text-green-600 font-semibold mb-1')
                            for note in related_notes[:3]:  # Show first 3 notes
                                note_name = note['name'][:30] + ('...' if len(note['name']) > 30 else '')
                                ui.label(f'• {note_name}').classes('text-xs text-gray-600 ml-2')
                            
                            if len(related_notes) > 3:
                                ui.label(f'... and {len(related_notes) - 3} more').classes('text-xs text-gray-500 ml-2')
                        else:
                            ui.label('📄 No related notes found').classes('text-sm text-gray-500')
                            
                            # Quick create button for this project
                            def create_note_for_project(pid=project_id):
                                note_path = pmbok_viewer.create_dendron_project_note(pid, dendron_status['vault_path'])
                                if note_path:
                                    ui.notify(f'✅ Created note for Project {pid}', type='positive')
                                else:
                                    ui.notify(f'❌ Failed to create note for Project {pid}', type='negative')
                            
                            ui.button('Create Note', on_click=create_note_for_project).classes('bg-blue-500 text-white text-xs mt-1')
    else:
        # Setup instructions
        with ui.card().classes('w-full p-6'):
            ui.label('🛠️ Setup Instructions').classes('text-2xl font-bold mb-4 text-blue-700')
            
            setup_steps = [
                "1. Install Dendron extension in VS Code",
                "2. Initialize a Dendron workspace",
                "3. Set DENDRON environment variable in .env file pointing to your vault path",
                "4. Ensure the dendron.yml configuration file exists in your vault",
                "5. Restart the PMBOK portal to detect your vault"
            ]
            
            for step in setup_steps:
                ui.label(step).classes('text-sm text-gray-700 mb-2')
            
            # Environment variable example
            with ui.card().classes('bg-gray-50 p-4 mt-4'):
                ui.label('Example .env configuration:').classes('text-sm font-semibold text-gray-700 mb-2')
                ui.label('DENDRON=/home/username/path/to/your/dendron/vault').classes('text-xs font-mono text-gray-600')
            
            ui.label('📖 Learn more about Dendron: https://www.dendron.so/').classes('text-sm text-blue-600 mt-4')


if __name__ in {"__main__", "__mp_main__"}:
    print("🚀 Starting PMBOK-Aligned Caribou Portal...")
    print("📊 Loading project portfolio...")
    
    if not os.path.exists(json_file_path):
        print("❌ JSON file not found. Please run enhanced_get_projects.py first.")
        exit(1)
    
    count = pmbok_viewer.refresh_data()
    metrics = pmbok_viewer.get_project_metrics()
    
    print(f"✅ Portfolio loaded: {count} projects")
    print(f"📈 Health: {metrics.get('on_track_count', 0)} on track, {metrics.get('at_risk_count', 0)} at risk, {metrics.get('overdue_count', 0)} overdue")
    print("🌐 Starting PMBOK dashboard...")
    print("📱 Portfolio Dashboard: http://localhost:8080")
    print("📊 PMBOK Report: http://localhost:8080/pmbok-report")
    print("🔍 Project Analysis: http://localhost:8080/pmbok/{project_id}")
    print("🌿 Dendron Integration: http://localhost:8080/dendron-integration")
    
    ui.run(
        host='0.0.0.0',
        port=8080,
        title='PMBOK Caribou Portal - Project Portfolio Management',
        reload=True,
        show=False
    )
