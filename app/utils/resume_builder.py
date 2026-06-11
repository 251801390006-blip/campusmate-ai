"""
Resume Builder 5.0 - Multi-Template, Live Preview, ATS Analysis
"""
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class ResumeTemplate:
    """Resume template management"""
    
    TEMPLATES = {
        'ats-classic': {'name': 'ATS Classic', 'category': 'ATS Friendly', 'colors': {'primary': '#2c3e50'}},
        'modern-teal': {'name': 'Modern Teal', 'category': 'Modern', 'colors': {'primary': '#16a085'}},
        'minimalist': {'name': 'Minimalist', 'category': 'Minimal', 'colors': {'primary': '#34495e'}},
        'executive': {'name': 'Executive', 'category': 'Professional', 'colors': {'primary': '#2980b9'}},
    }
    
    @classmethod
    def get_all(cls) -> List[Dict]:
        return list(cls.TEMPLATES.values())
    
    @classmethod
    def get_template(cls, template_id: str) -> Optional[Dict]:
        return cls.TEMPLATES.get(template_id)


class ATSAnalyzer:
    """ATS Resume Analysis Engine"""
    
    def __init__(self):
        self.keyword_database = self._load_keywords()
    
    def _load_keywords(self) -> Dict[str, List[str]]:
        return {
            'python': ['python', 'django', 'flask', 'pandas', 'numpy', 'pytest'],
            'javascript': ['javascript', 'node.js', 'react', 'vue', 'typescript', 'webpack'],
            'cloud': ['aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform'],
            'databases': ['postgresql', 'mysql', 'mongodb', 'redis', 'sql'],
            'soft_skills': ['leadership', 'communication', 'teamwork', 'problem-solving'],
        }
    
    def calculate_score(self, resume_data: Dict) -> Dict[str, Any]:
        """Calculate comprehensive ATS score"""
        try:
            text = self._extract_text(resume_data)
            text_lower = text.lower()
            
            # Keyword matching
            keyword_score = self._calculate_keyword_score(text_lower)
            
            # Formatting score
            formatting_score = self._calculate_formatting_score(resume_data)
            
            # Skills detection
            skills_score = self._detect_skills(resume_data)
            
            # Overall score
            overall = (keyword_score * 0.35) + (formatting_score * 0.30) + (skills_score * 0.35)
            
            return {
                'overall_score': round(overall, 1),
                'keyword_score': round(keyword_score, 1),
                'formatting_score': round(formatting_score, 1),
                'skills_score': round(skills_score, 1),
                'suggestions': self._generate_suggestions(resume_data, text_lower),
                'missing_keywords': self._find_missing_keywords(text_lower),
            }
        except Exception as e:
            logger.error(f"Error calculating ATS score: {str(e)}")
            return {'overall_score': 0, 'error': 'Analysis failed'}
    
    def _extract_text(self, resume_data: Dict) -> str:
        """Extract all text from resume data"""
        text_parts = []
        for section in resume_data.values():
            if isinstance(section, str):
                text_parts.append(section)
            elif isinstance(section, dict):
                text_parts.extend(section.values())
            elif isinstance(section, list):
                for item in section:
                    if isinstance(item, dict):
                        text_parts.extend(item.values())
                    elif isinstance(item, str):
                        text_parts.append(item)
        return ' '.join(str(p) for p in text_parts)
    
    def _calculate_keyword_score(self, text_lower: str) -> float:
        """Score based on keyword presence"""
        found_keywords = 0
        total_keywords = sum(len(v) for v in self.keyword_database.values())
        
        for keywords in self.keyword_database.values():
            for keyword in keywords:
                if keyword in text_lower:
                    found_keywords += 1
        
        return (found_keywords / total_keywords * 100) if total_keywords > 0 else 0
    
    def _calculate_formatting_score(self, resume_data: Dict) -> float:
        """Score formatting and structure"""
        score = 50  # Base score
        
        # Check for required sections
        required_sections = ['name', 'email', 'phone', 'summary', 'experience', 'education']
        for section in required_sections:
            if section in resume_data and resume_data[section]:
                score += 5
        
        return min(score, 100)
    
    def _detect_skills(self, resume_data: Dict) -> float:
        """Detect and score technical skills"""
        skills_section = resume_data.get('skills', [])
        if isinstance(skills_section, list) and len(skills_section) > 0:
            return min(len(skills_section) * 5, 100)
        return 30
    
    def _generate_suggestions(self, resume_data: Dict, text_lower: str) -> List[str]:
        """Generate ATS improvement suggestions"""
        suggestions = []
        
        if not text_lower or len(text_lower) < 100:
            suggestions.append("Add more content to your resume")
        
        if 'summary' not in resume_data or not resume_data.get('summary'):
            suggestions.append("Add a professional summary")
        
        if 'skills' not in resume_data or not resume_data.get('skills'):
            suggestions.append("Add a skills section with technical proficiencies")
        
        if len(resume_data.get('experience', [])) < 1:
            suggestions.append("Add work experience details")
        
        if len(suggestions) == 0:
            suggestions.append("Resume looks great! Consider adding certifications")
        
        return suggestions
    
    def _find_missing_keywords(self, text_lower: str) -> List[str]:
        """Find commonly used keywords missing from resume"""
        missing = []
        
        for category, keywords in self.keyword_database.items():
            found = [kw for kw in keywords if kw in text_lower]
            if len(found) == 0:
                missing.extend(keywords[:2])  # Add first 2 keywords from missing category
        
        return list(set(missing))[:10]  # Return unique, top 10


class ResumeDataExtractor:
    """Extract resume data from uploaded files (PDF/DOCX)"""
    
    @staticmethod
    def extract_from_text(text: str) -> Dict[str, Any]:
        """Extract structured data from resume text"""
        try:
            extracted = {
                'name': ResumeDataExtractor._extract_name(text),
                'email': ResumeDataExtractor._extract_email(text),
                'phone': ResumeDataExtractor._extract_phone(text),
                'summary': text[:200] if text else '',
                'experience': [],
                'education': [],
                'skills': ResumeDataExtractor._extract_skills(text),
            }
            return extracted
        except Exception as e:
            logger.error(f"Error extracting resume data: {str(e)}")
            return {}
    
    @staticmethod
    def _extract_email(text: str) -> str:
        """Extract email address"""
        import re
        match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
        return match.group(0) if match else ''
    
    @staticmethod
    def _extract_phone(text: str) -> str:
        """Extract phone number"""
        import re
        match = re.search(r'[\+]?[\d\s\-\(\)]{10,}', text)
        return match.group(0).strip() if match else ''
    
    @staticmethod
    def _extract_name(text: str) -> str:
        """Extract likely name from first line"""
        lines = text.strip().split('\n')
        return lines[0][:50] if lines else ''
    
    @staticmethod
    def _extract_skills(text: str) -> List[str]:
        """Extract likely skills"""
        tech_keywords = ['python', 'javascript', 'java', 'c++', 'react', 'django', 'aws', 'sql', 'git', 'docker']
        found_skills = []
        text_lower = text.lower()
        
        for skill in tech_keywords:
            if skill in text_lower:
                found_skills.append(skill)
        
        return found_skills[:10]


class ResumeLivePreview:
    """Generate live preview HTML for resume"""
    
    @staticmethod
    def generate_html(resume_data: Dict, template: str = 'ats-classic') -> str:
        """Generate HTML preview from resume data"""
        try:
            html = f"""
            <div class="resume-preview-container" data-template="{template}">
                <div class="resume-header">
                    <h1>{resume_data.get('name', 'Your Name')}</h1>
                    <p class="contact-info">
                        {resume_data.get('email', '')} | {resume_data.get('phone', '')}
                    </p>
                </div>
                
                <div class="resume-summary">
                    <h2>Professional Summary</h2>
                    <p>{resume_data.get('summary', '')}</p>
                </div>
                
                <div class="resume-experience">
                    <h2>Experience</h2>
                    {ResumeLivePreview._render_experience(resume_data.get('experience', []))}
                </div>
                
                <div class="resume-education">
                    <h2>Education</h2>
                    {ResumeLivePreview._render_education(resume_data.get('education', []))}
                </div>
                
                <div class="resume-skills">
                    <h2>Skills</h2>
                    <div class="skills-list">
                        {ResumeLivePreview._render_skills(resume_data.get('skills', []))}
                    </div>
                </div>
            </div>
            """
            return html
        except Exception as e:
            logger.error(f"Error generating preview: {str(e)}")
            return "<p>Error generating preview</p>"
    
    @staticmethod
    def _render_experience(experience: List[Dict]) -> str:
        html = ""
        for job in experience:
            html += f"""
            <div class="experience-item">
                <div class="job-header">
                    <h3>{job.get('title', '')}</h3>
                    <span class="job-date">{job.get('start_date', '')} - {job.get('end_date', '')}</span>
                </div>
                <p class="company">{job.get('company', '')}</p>
                <p class="description">{job.get('description', '')}</p>
            </div>
            """
        return html
    
    @staticmethod
    def _render_education(education: List[Dict]) -> str:
        html = ""
        for edu in education:
            html += f"""
            <div class="education-item">
                <h3>{edu.get('degree', '')}</h3>
                <p>{edu.get('school', '')}</p>
                <p class="graduation">{edu.get('graduation_year', '')}</p>
            </div>
            """
        return html
    
    @staticmethod
    def _render_skills(skills: List[str]) -> str:
        return ''.join(f'<span class="skill-tag">{skill}</span>' for skill in skills)
