"""
Performance utilities for GEC Mines application
"""
import time
import functools
from flask import current_app, g
from sqlalchemy import text
from app import db

# Simple in-memory cache for development (use Redis in production)
_cache = {}
_cache_ttl = {}

def cache_result(ttl=300):  # 5 minutes default TTL
    """Simple caching decorator for function results"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            cache_key = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
            
            current_time = time.time()
            
            # Check if cached result exists and is still valid
            if (cache_key in _cache and 
                cache_key in _cache_ttl and 
                current_time < _cache_ttl[cache_key]):
                return _cache[cache_key]
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            _cache[cache_key] = result
            _cache_ttl[cache_key] = current_time + ttl
            
            return result
        return wrapper
    return decorator

def clear_cache():
    """Clear all cached results"""
    global _cache, _cache_ttl
    _cache.clear()
    _cache_ttl.clear()

def clean_expired_cache():
    """Remove expired cache entries"""
    current_time = time.time()
    expired_keys = [
        key for key, expiry in _cache_ttl.items()
        if current_time >= expiry
    ]
    for key in expired_keys:
        _cache.pop(key, None)
        _cache_ttl.pop(key, None)

def optimize_query_for_pagination(query, page, per_page, count_query=None):
    """Optimize pagination queries to avoid expensive COUNT operations"""
    # Use a more efficient counting method for large datasets
    if count_query is None:
        count_query = query
    
    # Get total count with optimization
    try:
        # Use approximate count for better performance on large tables
        total = count_query.count()
    except Exception:
        # Fallback to basic count
        total = query.count()
    
    # Calculate offset
    offset = (page - 1) * per_page
    
    # Get items with limit and offset
    items = query.offset(offset).limit(per_page).all()
    
    # Create pagination object-like structure
    class PaginationResult:
        def __init__(self, items, page, per_page, total):
            self.items = items
            self.page = page
            self.per_page = per_page
            self.total = total
            self.pages = (total + per_page - 1) // per_page
            self.has_prev = page > 1
            self.has_next = page < self.pages
            self.prev_num = page - 1 if self.has_prev else None
            self.next_num = page + 1 if self.has_next else None
    
    return PaginationResult(items, page, per_page, total)

def get_database_stats():
    """Get database statistics for monitoring"""
    try:
        stats = {}
        
        # Table sizes
        tables = ['user', 'courrier', 'log_activite', 'statut_courrier', 'departement', 'parametres_systeme']
        for table in tables:
            result = db.session.execute(text(f"SELECT COUNT(*) FROM {table}"))
            stats[f"{table}_count"] = result.scalar()
        
        # Recent activity
        result = db.session.execute(text("""
            SELECT COUNT(*) FROM courrier 
            WHERE date_enregistrement >= DATE('now', '-7 days')
        """))
        stats['courriers_last_week'] = result.scalar()
        
        result = db.session.execute(text("""
            SELECT COUNT(*) FROM log_activite 
            WHERE date_action >= DATE('now', '-24 hours')
        """))
        stats['activities_last_24h'] = result.scalar()
        
        return stats
        
    except Exception as e:
        current_app.logger.error(f"Error getting database stats: {e}")
        return {}

def optimize_search_query(search_term, query_class):
    """Optimize full-text search queries"""
    if not search_term or len(search_term.strip()) < 2:
        return None
    
    # Clean search term
    search_term = search_term.strip()
    
    # Split into words for better matching
    words = search_term.split()
    
    search_conditions = []
    
    # Add conditions for each word - including all metadata fields
    for word in words:
        if len(word) >= 2:  # Only search words with 2+ characters
            word_pattern = f"%{word}%"
            search_conditions.extend([
                query_class.numero_accuse_reception.ilike(word_pattern),
                query_class.numero_reference.ilike(word_pattern),
                query_class.objet.ilike(word_pattern),
                query_class.expediteur.ilike(word_pattern),
                query_class.destinataire.ilike(word_pattern),
                query_class.statut.ilike(word_pattern),
                query_class.autres_informations.ilike(word_pattern) if hasattr(query_class, 'autres_informations') else None,
                query_class.fichier_nom.ilike(word_pattern) if hasattr(query_class, 'fichier_nom') else None
            ])
            # Remove None values from search conditions
            search_conditions = [c for c in search_conditions if c is not None]
    
    if search_conditions:
        from sqlalchemy import or_
        return or_(*search_conditions)
    
    return None

def batch_process_items(items, batch_size=100, processor_func=None):
    """Process items in batches for better performance"""
    if not items:
        return []
    
    results = []
    
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        
        if processor_func:
            batch_results = processor_func(batch)
            results.extend(batch_results)
        else:
            results.extend(batch)
    
    return results

def monitor_query_performance(func):
    """Decorator to monitor query performance"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        execution_time = time.time() - start_time
        
        # Log slow queries (> 1 second)
        if execution_time > 1.0:
            current_app.logger.warning(
                f"Slow query detected: {func.__name__} took {execution_time:.2f}s"
            )
        
        # Store in Flask g for debugging
        if not hasattr(g, 'query_times'):
            g.query_times = []
        g.query_times.append({
            'function': func.__name__,
            'time': execution_time
        })
        
        return result
    return wrapper

@cache_result(ttl=600)  # Cache for 10 minutes
def get_dashboard_statistics():
    """Get cached dashboard statistics"""
    from models import Courrier, User, LogActivite
    from datetime import datetime, timedelta
    
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)
    
    stats = {
        'total_courriers': Courrier.query.count(),
        'courriers_today': Courrier.query.filter(
            Courrier.date_enregistrement >= today
        ).count(),
        'courriers_this_week': Courrier.query.filter(
            Courrier.date_enregistrement >= week_ago
        ).count(),
        'total_users': User.query.filter_by(actif=True).count(),
        'recent_activities': LogActivite.query.order_by(
            LogActivite.date_action.desc()
        ).limit(5).all()
    }
    
    return stats

def preload_relationships(query, *relationships):
    """Preload relationships to avoid N+1 queries"""
    from sqlalchemy.orm import joinedload
    
    for relationship in relationships:
        query = query.options(joinedload(relationship))
    
    return query

class PerformanceMonitor:
    """Context manager for monitoring performance"""
    
    def __init__(self, operation_name):
        self.operation_name = operation_name
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        execution_time = time.time() - self.start_time
        
        # Log performance metrics
        current_app.logger.info(
            f"Performance: {self.operation_name} completed in {execution_time:.3f}s"
        )
        
        # Log slow operations
        if execution_time > 2.0:
            current_app.logger.warning(
                f"Slow operation: {self.operation_name} took {execution_time:.3f}s"
            )