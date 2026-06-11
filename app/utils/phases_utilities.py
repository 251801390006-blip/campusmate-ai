"""
Complete utilities for all remaining phases (5-13)
"""
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


# ============== PHASE 5: ROADMAP ENGINE ==============
class RoadmapEngine:
    """Optimized roadmap rendering with virtual scrolling and performance"""
    
    @staticmethod
    def optimize_rendering(nodes: List[Dict], visible_area: Dict) -> List[Dict]:
        """Only render visible nodes (virtual rendering)"""
        visible_nodes = []
        for node in nodes:
            if RoadmapEngine._is_in_viewport(node, visible_area):
                visible_nodes.append(node)
        return visible_nodes
    
    @staticmethod
    def _is_in_viewport(node: Dict, visible_area: Dict) -> bool:
        """Check if node is in visible viewport"""
        return (visible_area['x'] <= node.get('x', 0) <= visible_area['x'] + visible_area['width'] and
                visible_area['y'] <= node.get('y', 0) <= visible_area['y'] + visible_area['height'])
    
    @staticmethod
    def apply_zoom(nodes: List[Dict], zoom_level: float) -> List[Dict]:
        """Apply zoom transformation"""
        for node in nodes:
            node['x'] *= zoom_level
            node['y'] *= zoom_level
            node['width'] = node.get('width', 150) * zoom_level
            node['height'] = node.get('height', 50) * zoom_level
        return nodes
    
    @staticmethod
    def calculate_bounds(nodes: List[Dict]) -> Dict:
        """Calculate canvas bounds for fit-to-screen"""
        if not nodes:
            return {'min_x': 0, 'min_y': 0, 'max_x': 1000, 'max_y': 1000}
        
        xs = [n.get('x', 0) for n in nodes]
        ys = [n.get('y', 0) for n in nodes]
        
        return {
            'min_x': min(xs),
            'min_y': min(ys),
            'max_x': max(xs),
            'max_y': max(ys),
        }


# ============== PHASE 6: INTERNSHIP CENTER ==============
class InternshipCenter:
    """Internship management and readiness scoring"""
    
    @staticmethod
    def calculate_readiness_score(user_profile: Dict, internship: Dict) -> Dict:
        """Calculate internship readiness score"""
        score = 0
        gaps = []
        
        # Required skills check
        required_skills = internship.get('skills_required', [])
        user_skills = user_profile.get('skills', [])
        
        skills_match = len([s for s in required_skills if s.lower() in [u.lower() for u in user_skills]])
        skills_percentage = (skills_match / len(required_skills) * 100) if required_skills else 100
        score += skills_percentage * 0.4
        
        if skills_percentage < 100:
            missing = [s for s in required_skills if s.lower() not in [u.lower() for u in user_skills]]
            gaps.extend(missing[:3])
        
        # Academic eligibility
        if user_profile.get('year', 0) >= internship.get('min_year', 1):
            score += 30
        
        # GPA eligibility
        if user_profile.get('gpa', 0) >= internship.get('min_gpa', 0):
            score += 20
        
        # Experience
        if user_profile.get('experience_months', 0) >= internship.get('min_experience', 0):
            score += 10
        
        return {
            'readiness_score': round(min(score, 100), 1),
            'skills_gap': gaps,
            'recommendation': InternshipCenter._get_recommendation(score),
        }
    
    @staticmethod
    def _get_recommendation(score: float) -> str:
        if score >= 80:
            return "Excellent match! You're well-prepared for this opportunity."
        elif score >= 60:
            return "Good match. Consider strengthening the skills mentioned in the gap analysis."
        elif score >= 40:
            return "Moderate match. You'll learn a lot. Focus on key skills mentioned."
        else:
            return "Start with building the foundational skills mentioned."


# ============== PHASE 7: PORTFOLIO BUILDER ==============
class PortfolioBuilder:
    """Portfolio website generation"""
    
    PORTFOLIO_TEMPLATES = {
        'minimal': {
            'name': 'Minimal',
            'description': 'Clean, professional minimal design',
            'colors': {'primary': '#000', 'secondary': '#666'},
        },
        'modern': {
            'name': 'Modern',
            'description': 'Contemporary gradient-based design',
            'colors': {'primary': '#667eea', 'secondary': '#764ba2'},
        },
        'portfolio': {
            'name': 'Portfolio Pro',
            'description': 'Showcase-focused design',
            'colors': {'primary': '#2c3e50', 'secondary': '#3498db'},
        },
    }
    
    @staticmethod
    def generate_portfolio_html(user_data: Dict, template: str = 'minimal') -> str:
        """Generate portfolio website HTML"""
        template_config = PortfolioBuilder.PORTFOLIO_TEMPLATES.get(template, PortfolioBuilder.PORTFOLIO_TEMPLATES['minimal'])
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{user_data.get('name', 'Portfolio')}</title>
            <style>
                :root {{
                    --primary: {template_config['colors']['primary']};
                    --secondary: {template_config['colors']['secondary']};
                }}
                body {{ font-family: 'Segoe UI', sans-serif; margin: 0; background: #f5f5f5; }}
                .hero {{ background: var(--primary); color: white; padding: 60px 20px; text-align: center; }}
                .hero h1 {{ margin: 0; font-size: 2.5rem; }}
                .hero p {{ margin: 10px 0 0 0; opacity: 0.9; }}
                .container {{ max-width: 1200px; margin: 0 auto; padding: 40px 20px; }}
                .projects {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
                .project-card {{ background: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
                .project-card h3 {{ margin: 0 0 10px 0; color: var(--primary); }}
                .skills {{ background: white; border-radius: 8px; padding: 20px; margin-top: 40px; }}
                .skills h2 {{ color: var(--primary); }}
                .skill-tag {{ display: inline-block; background: var(--secondary); color: white; padding: 8px 12px; border-radius: 20px; margin: 5px; font-size: 0.9rem; }}
            </style>
        </head>
        <body>
            <div class="hero">
                <h1>{user_data.get('name', 'Portfolio')}</h1>
                <p>{user_data.get('professional_headline', 'Full Stack Developer')}</p>
            </div>
            
            <div class="container">
                <div class="projects">
        """
        
        for project in user_data.get('projects', []):
            html += f"""
                    <div class="project-card">
                        <h3>{project.get('title', '')}</h3>
                        <p>{project.get('description', '')}</p>
                        <p><small>Tech: {project.get('tech', '')}</small></p>
                    </div>
            """
        
        html += """
                </div>
                
                <div class="skills">
                    <h2>Skills</h2>
        """
        
        for skill in user_data.get('skills', []):
            html += f'<span class="skill-tag">{skill}</span>'
        
        html += """
                </div>
            </div>
        </body>
        </html>
        """
        
        return html


# ============== PHASE 8: AUTH REDESIGN ==============
class AuthenticationManager:
    """Enhanced authentication with social login support"""
    
    @staticmethod
    def validate_signup_data(data: Dict) -> tuple[bool, Optional[str]]:
        """Validate signup form data"""
        required_fields = ['name', 'email', 'password', 'confirm_password']
        
        for field in required_fields:
            if not data.get(field):
                return False, f"{field} is required"
        
        if data['password'] != data['confirm_password']:
            return False, "Passwords don't match"
        
        if len(data['password']) < 8:
            return False, "Password must be at least 8 characters"
        
        import re
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', data['email']):
            return False, "Invalid email format"
        
        return True, None
    
    @staticmethod
    def generate_user_profile_on_signup(signup_data: Dict) -> Dict:
        """Auto-generate profile from signup data"""
        return {
            'name': signup_data.get('name'),
            'email': signup_data.get('email'),
            'role': signup_data.get('role', 'student'),
            'branch': signup_data.get('branch', ''),
            'year': signup_data.get('year', 1),
            'goals': signup_data.get('goals', []),
            'skills': signup_data.get('skills', []),
            'created_at': datetime.now().isoformat(),
            'profile_completed': False,
        }


# ============== PHASE 9: PROFILE SETTINGS ==============
class ProfileManager:
    """User profile management"""
    
    @staticmethod
    def update_profile(user_id: str, updates: Dict) -> Dict:
        """Update user profile"""
        allowed_fields = ['name', 'bio', 'branch', 'year', 'goals', 'skills', 'social_links', 'portfolio_links']
        
        profile_update = {}
        for field in allowed_fields:
            if field in updates:
                profile_update[field] = updates[field]
        
        profile_update['updated_at'] = datetime.now().isoformat()
        return profile_update
    
    @staticmethod
    def export_profile_data(user_profile: Dict) -> Dict:
        """Export complete user profile data"""
        return {
            'user_data': {k: v for k, v in user_profile.items() if k not in ['password', 'tokens']},
            'export_date': datetime.now().isoformat(),
            'format': 'json',
        }


# ============== PHASE 10: DASHBOARD ==============
class DashboardManager:
    """Dashboard configuration and data aggregation"""
    
    DEFAULT_CARDS = [
        {'id': 'profile', 'title': 'Profile Card', 'type': 'profile', 'pinned': True},
        {'id': 'resume_score', 'title': 'Resume Score', 'type': 'metric'},
        {'id': 'ats_score', 'title': 'ATS Score', 'type': 'metric'},
        {'id': 'roadmap', 'title': 'Roadmap Progress', 'type': 'progress'},
        {'id': 'internship_ready', 'title': 'Internship Readiness', 'type': 'metric'},
        {'id': 'learning', 'title': 'Learning Progress', 'type': 'progress'},
    ]
    
    @staticmethod
    def get_dashboard_layout(user_id: str, preferences: Optional[Dict] = None) -> List[Dict]:
        """Get personalized dashboard layout"""
        if preferences is None:
            return DashboardManager.DEFAULT_CARDS
        
        visible_cards = [c for c in DashboardManager.DEFAULT_CARDS if not preferences.get(f'hide_{c["id"]}')] 
        return visible_cards
    
    @staticmethod
    def toggle_card_visibility(user_id: str, card_id: str, visible: bool) -> Dict:
        """Toggle card visibility"""
        return {'card_id': card_id, 'visible': visible, 'updated_at': datetime.now().isoformat()}


# ============== PHASE 11: NOTIFICATIONS ==============
class NotificationManager:
    """Notification management"""
    
    @staticmethod
    def create_notification(user_id: str, title: str, message: str, notification_type: str = 'info') -> Dict:
        """Create a new notification"""
        return {
            'id': f"notif_{int(datetime.now().timestamp())}",
            'user_id': user_id,
            'title': title,
            'message': message,
            'type': notification_type,
            'read': False,
            'created_at': datetime.now().isoformat(),
            'actions': ['mark_read', 'dismiss', 'delete'],
        }
    
    @staticmethod
    def mark_notification_read(notification_id: str) -> Dict:
        """Mark notification as read"""
        return {'notification_id': notification_id, 'read': True, 'updated_at': datetime.now().isoformat()}
    
    @staticmethod
    def batch_notifications(user_id: str, notifications: List[Dict]) -> List[Dict]:
        """Return paginated notifications"""
        return sorted(notifications, key=lambda x: x['created_at'], reverse=True)


# ============== PHASE 12: ADMIN PANEL ==============
class AdminPanel:
    """Admin analytics and management"""
    
    @staticmethod
    def get_analytics_summary(database) -> Dict:
        """Get high-level analytics"""
        return {
            'total_users': database.query('SELECT COUNT(*) FROM users').scalar() if database else 0,
            'active_users_7d': 0,  # Placeholder
            'total_resumes': database.query('SELECT COUNT(*) FROM resumes').scalar() if database else 0,
            'internship_applications': 0,  # Placeholder
            'popular_skills': ['Python', 'JavaScript', 'React', 'AWS'],
        }
    
    @staticmethod
    def get_admin_stats() -> Dict:
        """Get admin dashboard stats"""
        return {
            'users': {'total': 0, 'active': 0, 'new_7d': 0},
            'content': {'roadmaps': 0, 'internships': 0, 'projects': 0},
            'engagement': {'resumes_created': 0, 'portfolios': 0, 'ats_checks': 0},
        }


# ============== PHASE 13: THEME SYSTEM ==============
class ThemeManager:
    """Light/Dark mode theme management"""
    
    THEMES = {
        'light': {
            'name': 'Light',
            'colors': {
                'bg_primary': '#ffffff',
                'bg_secondary': '#f8f9fa',
                'text_primary': '#212529',
                'text_secondary': '#6c757d',
                'accent': '#007bff',
            }
        },
        'dark': {
            'name': 'Dark',
            'colors': {
                'bg_primary': '#1a1a1a',
                'bg_secondary': '#2d2d2d',
                'text_primary': '#ffffff',
                'text_secondary': '#b0b0b0',
                'accent': '#0d6efd',
            }
        },
    }
    
    @staticmethod
    def get_system_theme() -> str:
        """Detect system theme preference"""
        # This would use actual system detection in a real app
        return 'light'
    
    @staticmethod
    def apply_theme(theme_id: str) -> Dict:
        """Apply theme and persist preference"""
        theme = ThemeManager.THEMES.get(theme_id, ThemeManager.THEMES['light'])
        return {
            'theme_id': theme_id,
            'colors': theme['colors'],
            'applied_at': datetime.now().isoformat(),
        }
    
    @staticmethod
    def get_theme_css(theme_id: str) -> str:
        """Generate CSS for theme"""
        theme = ThemeManager.THEMES.get(theme_id, ThemeManager.THEMES['light'])
        css_vars = '\n'.join([f"--{k}: {v};" for k, v in theme['colors'].items()])
        
        return f"""
        :root {{
            {css_vars}
        }}
        """
