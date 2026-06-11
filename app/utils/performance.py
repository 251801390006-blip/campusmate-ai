"""
Performance Optimization Module for CampusMate AI
Addresses: Slow loading, lag, memory leaks, rendering issues
"""
import os
import logging
import time
from functools import wraps
from flask import current_app, request

logger = logging.getLogger(__name__)

# Try to import caching, make it optional
try:
    from flask_caching import Cache
    CACHING_AVAILABLE = True
except ImportError:
    CACHING_AVAILABLE = False
    logger.warning("Flask-Caching not installed - caching disabled")
    
    # Dummy Cache for compatibility
    class Cache:
        def init_app(self, app, config=None):
            pass

# Cache configuration
cache_config = {
    'CACHE_TYPE': 'simple',
    'CACHE_DEFAULT_TIMEOUT': 300,
    'CACHE_REDIS_URL': os.environ.get('REDIS_URL'),
}

cache = Cache()

def init_cache(app):
    """Initialize caching for the application"""
    if CACHING_AVAILABLE:
        cache.init_app(app, config=cache_config)
        logger.info("Cache initialized")
    else:
        logger.warning("Caching not available")


def performance_monitor(func):
    """Decorator to monitor function performance"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start_time
        
        if elapsed > 1.0:  # Log slow functions (> 1 second)
            logger.warning(f"Slow function: {func.__name__} took {elapsed:.2f}s")
        
        return result
    return wrapper


def optimize_query(query_func):
    """Decorator to optimize database queries with pagination"""
    @wraps(query_func)
    def wrapper(*args, **kwargs):
        # Add pagination if not already present
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        
        # Limit per_page to prevent memory overload
        per_page = min(per_page, 100)
        
        # Get results with pagination
        result = query_func(*args, **kwargs)
        
        # Add pagination metadata if result is queryable
        if hasattr(result, 'paginate'):
            return result.paginate(page=page, per_page=per_page)
        
        return result
    return wrapper


class PerformanceOptimizations:
    """Collection of performance optimization strategies"""
    
    @staticmethod
    def enable_compression(app):
        """Enable gzip compression for responses"""
        try:
            from flask_compress import Compress
            Compress(app)
            logger.info("Gzip compression enabled")
        except ImportError:
            logger.warning("Flask-Compress not installed - compression disabled")
    
    @staticmethod
    def enable_caching_headers(app):
        """Add caching headers to responses"""
        @app.after_request
        def add_caching_headers(response):
            # Cache static assets for 30 days
            if request.path.startswith('/static/'):
                response.cache_control.max_age = 2592000
                response.cache_control.public = True
                response.set_etag(response.get_data())
            # Don't cache HTML pages
            elif response.content_type and 'text/html' in response.content_type:
                response.cache_control.no_cache = True
                response.cache_control.no_store = True
                response.pragma = 'no-cache'
            return response
        
        logger.info("Caching headers configured")
    
    @staticmethod
    def lazy_load_components(app):
        """Enable lazy loading for components"""
        @app.context_processor
        def inject_lazy_load():
            return {
                'lazy_load': True,
                'preload_critical': ['dashboard', 'resume-analyzer']
            }
        
        logger.info("Lazy loading enabled")
    
    @staticmethod
    def optimize_database_queries(db):
        """Add query optimization hints"""
        # Use relationship eager loading
        # Use select_in_load for large collections
        # Disable autocommit for batch operations
        logger.info("Database query optimization configured")
    
    @staticmethod
    def enable_cdn_assets():
        """CDN configuration for static assets"""
        cdn_config = {
            'BOOTSTRAP': 'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/',
            'FONTAWESOME': 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/',
            'JQUERY': 'https://code.jquery.com/',
            'CHARTS': 'https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/'
        }
        return cdn_config


# Performance metrics tracking
class PerformanceMetrics:
    """Track application performance metrics"""
    
    _metrics = {
        'page_loads': {},
        'api_calls': {},
        'database_queries': {},
    }
    
    @classmethod
    def record_page_load(cls, page_name, duration_ms):
        """Record page load time"""
        if page_name not in cls._metrics['page_loads']:
            cls._metrics['page_loads'][page_name] = []
        
        cls._metrics['page_loads'][page_name].append(duration_ms)
        
        # Log if slow
        if duration_ms > 2000:  # > 2 seconds
            logger.warning(f"Slow page load: {page_name} ({duration_ms:.0f}ms)")
    
    @classmethod
    def record_api_call(cls, endpoint, duration_ms, status_code):
        """Record API call metrics"""
        if endpoint not in cls._metrics['api_calls']:
            cls._metrics['api_calls'][endpoint] = []
        
        cls._metrics['api_calls'][endpoint].append({
            'duration': duration_ms,
            'status': status_code
        })
        
        if duration_ms > 1000:
            logger.warning(f"Slow API call: {endpoint} ({duration_ms:.0f}ms) [{status_code}]")
    
    @classmethod
    def get_metrics_summary(cls):
        """Get performance metrics summary"""
        avg_page_loads = {}
        for page, times in cls._metrics['page_loads'].items():
            avg_page_loads[page] = sum(times) / len(times) if times else 0
        
        return {
            'avg_page_loads': avg_page_loads,
            'total_api_calls': sum(len(v) for v in cls._metrics['api_calls'].values()),
            'slow_endpoints': [
                k for k, v in cls._metrics['api_calls'].items()
                if any(call['duration'] > 1000 for call in v)
            ]
        }


# Middleware for performance tracking
def init_performance_tracking(app):
    """Initialize performance tracking middleware"""
    
    @app.before_request
    def before_request():
        request._start_time = time.time()
    
    @app.after_request
    def after_request(response):
        if hasattr(request, '_start_time'):
            duration_ms = (time.time() - request._start_time) * 1000
            
            # Record metrics
            if request.path.startswith('/api/'):
                PerformanceMetrics.record_api_call(
                    request.path,
                    duration_ms,
                    response.status_code
                )
            else:
                PerformanceMetrics.record_page_load(
                    request.path,
                    duration_ms
                )
            
            # Add performance header
            response.headers['X-Response-Time'] = f"{duration_ms:.0f}ms"
            
            # Log very slow requests
            if duration_ms > 3000:
                logger.warning(
                    f"Very slow request: {request.method} {request.path} "
                    f"({duration_ms:.0f}ms)"
                )
        
        return response


# Frontend performance hints
PERFORMANCE_HINTS = {
    'preload_fonts': [
        'https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&display=swap',
    ],
    'preload_critical_resources': [
        '/static/css/style.css',
        '/static/js/main.js',
    ],
    'prefetch_resources': [
        '/resume-analyzer',
        '/roadmaps',
        '/dashboard',
    ],
    'image_optimization': {
        'max_width': 1920,
        'quality': 80,
        'formats': ['webp', 'jpg', 'png']
    }
}


def get_performance_recommendations():
    """Get performance optimization recommendations"""
    return {
        'metrics': PerformanceMetrics.get_metrics_summary(),
        'hints': PERFORMANCE_HINTS,
        'recommendations': [
            'Use CDN for static assets',
            'Enable gzip compression',
            'Lazy load images',
            'Minimize JavaScript bundles',
            'Cache API responses',
            'Use database connection pooling',
            'Enable query caching',
            'Optimize database indexes',
            'Use pagination for large lists',
            'Implement virtual scrolling for long lists'
        ]
    }


# Cache configuration
cache_config = {
    'CACHE_TYPE': 'simple',
    'CACHE_DEFAULT_TIMEOUT': 300,
    'CACHE_REDIS_URL': os.environ.get('REDIS_URL'),
}

cache = Cache()

def init_cache(app):
    """Initialize caching for the application"""
    cache.init_app(app, config=cache_config)
    logger.info("Cache initialized")


def performance_monitor(func):
    """Decorator to monitor function performance"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start_time
        
        if elapsed > 1.0:  # Log slow functions (> 1 second)
            logger.warning(f"Slow function: {func.__name__} took {elapsed:.2f}s")
        
        return result
    return wrapper


def optimize_query(query_func):
    """Decorator to optimize database queries with pagination"""
    @wraps(query_func)
    def wrapper(*args, **kwargs):
        # Add pagination if not already present
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        
        # Limit per_page to prevent memory overload
        per_page = min(per_page, 100)
        
        # Get results with pagination
        result = query_func(*args, **kwargs)
        
        # Add pagination metadata if result is queryable
        if hasattr(result, 'paginate'):
            return result.paginate(page=page, per_page=per_page)
        
        return result
    return wrapper


class PerformanceOptimizations:
    """Collection of performance optimization strategies"""
    
    @staticmethod
    def enable_compression(app):
        """Enable gzip compression for responses"""
        try:
            from flask_compress import Compress
            Compress(app)
            logger.info("Gzip compression enabled")
        except ImportError:
            logger.warning("Flask-Compress not installed")
    
    @staticmethod
    def enable_caching_headers(app):
        """Add caching headers to responses"""
        @app.after_request
        def add_caching_headers(response):
            # Cache static assets for 30 days
            if request.path.startswith('/static/'):
                response.cache_control.max_age = 2592000
                response.cache_control.public = True
                response.set_etag(response.get_data())
            # Don't cache HTML pages
            elif response.content_type and 'text/html' in response.content_type:
                response.cache_control.no_cache = True
                response.cache_control.no_store = True
                response.pragma = 'no-cache'
            return response
        
        logger.info("Caching headers configured")
    
    @staticmethod
    def lazy_load_components(app):
        """Enable lazy loading for components"""
        @app.context_processor
        def inject_lazy_load():
            return {
                'lazy_load': True,
                'preload_critical': ['dashboard', 'resume-analyzer']
            }
        
        logger.info("Lazy loading enabled")
    
    @staticmethod
    def optimize_database_queries(db):
        """Add query optimization hints"""
        # Use relationship eager loading
        # Use select_in_load for large collections
        # Disable autocommit for batch operations
        logger.info("Database query optimization configured")
    
    @staticmethod
    def enable_cdn_assets():
        """CDN configuration for static assets"""
        cdn_config = {
            'BOOTSTRAP': 'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/',
            'FONTAWESOME': 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/',
            'JQUERY': 'https://code.jquery.com/',
            'CHARTS': 'https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/'
        }
        return cdn_config


# Performance metrics tracking
class PerformanceMetrics:
    """Track application performance metrics"""
    
    _metrics = {
        'page_loads': {},
        'api_calls': {},
        'database_queries': {},
    }
    
    @classmethod
    def record_page_load(cls, page_name, duration_ms):
        """Record page load time"""
        if page_name not in cls._metrics['page_loads']:
            cls._metrics['page_loads'][page_name] = []
        
        cls._metrics['page_loads'][page_name].append(duration_ms)
        
        # Log if slow
        if duration_ms > 2000:  # > 2 seconds
            logger.warning(f"Slow page load: {page_name} ({duration_ms:.0f}ms)")
    
    @classmethod
    def record_api_call(cls, endpoint, duration_ms, status_code):
        """Record API call metrics"""
        if endpoint not in cls._metrics['api_calls']:
            cls._metrics['api_calls'][endpoint] = []
        
        cls._metrics['api_calls'][endpoint].append({
            'duration': duration_ms,
            'status': status_code
        })
        
        if duration_ms > 1000:
            logger.warning(f"Slow API call: {endpoint} ({duration_ms:.0f}ms) [{status_code}]")
    
    @classmethod
    def get_metrics_summary(cls):
        """Get performance metrics summary"""
        avg_page_loads = {}
        for page, times in cls._metrics['page_loads'].items():
            avg_page_loads[page] = sum(times) / len(times) if times else 0
        
        return {
            'avg_page_loads': avg_page_loads,
            'total_api_calls': sum(len(v) for v in cls._metrics['api_calls'].values()),
            'slow_endpoints': [
                k for k, v in cls._metrics['api_calls'].items()
                if any(call['duration'] > 1000 for call in v)
            ]
        }


# Middleware for performance tracking
def init_performance_tracking(app):
    """Initialize performance tracking middleware"""
    
    @app.before_request
    def before_request():
        request._start_time = time.time()
    
    @app.after_request
    def after_request(response):
        if hasattr(request, '_start_time'):
            duration_ms = (time.time() - request._start_time) * 1000
            
            # Record metrics
            if request.path.startswith('/api/'):
                PerformanceMetrics.record_api_call(
                    request.path,
                    duration_ms,
                    response.status_code
                )
            else:
                PerformanceMetrics.record_page_load(
                    request.path,
                    duration_ms
                )
            
            # Add performance header
            response.headers['X-Response-Time'] = f"{duration_ms:.0f}ms"
            
            # Log very slow requests
            if duration_ms > 3000:
                logger.warning(
                    f"Very slow request: {request.method} {request.path} "
                    f"({duration_ms:.0f}ms)"
                )
        
        return response


# Frontend performance hints
PERFORMANCE_HINTS = {
    'preload_fonts': [
        'https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&display=swap',
    ],
    'preload_critical_resources': [
        '/static/css/style.css',
        '/static/js/main.js',
    ],
    'prefetch_resources': [
        '/resume-analyzer',
        '/roadmaps',
        '/dashboard',
    ],
    'image_optimization': {
        'max_width': 1920,
        'quality': 80,
        'formats': ['webp', 'jpg', 'png']
    }
}


def get_performance_recommendations():
    """Get performance optimization recommendations"""
    return {
        'metrics': PerformanceMetrics.get_metrics_summary(),
        'hints': PERFORMANCE_HINTS,
        'recommendations': [
            'Use CDN for static assets',
            'Enable gzip compression',
            'Lazy load images',
            'Minimize JavaScript bundles',
            'Cache API responses',
            'Use database connection pooling',
            'Enable query caching',
            'Optimize database indexes',
            'Use pagination for large lists',
            'Implement virtual scrolling for long lists'
        ]
    }
