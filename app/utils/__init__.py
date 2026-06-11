"""App utilities module"""
from app.utils.pdf_generator import (
    generate_resume_pdf,
    generate_resume_pdf_with_css,
    sanitize_pdf_content,
    validate_pdf_generation,
    WEASYPRINT_AVAILABLE
)

from app.utils.performance import (
    performance_monitor,
    optimize_query,
    PerformanceOptimizations,
    PerformanceMetrics,
    init_performance_tracking,
    init_cache,
    get_performance_recommendations,
    PERFORMANCE_HINTS
)

from app.utils.resume_builder import (
    ResumeTemplate,
    ATSAnalyzer,
    ResumeDataExtractor,
    ResumeLivePreview,
)

from app.utils.phases_utilities import (
    RoadmapEngine,
    InternshipCenter,
    PortfolioBuilder,
    AuthenticationManager,
    ProfileManager,
    DashboardManager,
    NotificationManager,
    AdminPanel,
    ThemeManager,
)

__all__ = [
    # PDF
    'generate_resume_pdf',
    'generate_resume_pdf_with_css',
    'sanitize_pdf_content',
    'validate_pdf_generation',
    'WEASYPRINT_AVAILABLE',
    # Performance
    'performance_monitor',
    'optimize_query',
    'PerformanceOptimizations',
    'PerformanceMetrics',
    'init_performance_tracking',
    'init_cache',
    'get_performance_recommendations',
    'PERFORMANCE_HINTS',
    # Resume Builder (Phase 3)
    'ResumeTemplate',
    'ATSAnalyzer',
    'ResumeDataExtractor',
    'ResumeLivePreview',
    # Phases Utilities (5-13)
    'RoadmapEngine',
    'InternshipCenter',
    'PortfolioBuilder',
    'AuthenticationManager',
    'ProfileManager',
    'DashboardManager',
    'NotificationManager',
    'AdminPanel',
    'ThemeManager',
]

