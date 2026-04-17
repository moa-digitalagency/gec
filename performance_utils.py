"""
Performance utilities for GEC application.
Cache backend: Redis when available, in-memory dict as fallback.
Set REDIS_URL env var to enable Redis (e.g. redis://localhost:6379/0).
"""
import os
import time
import pickle
import functools
import logging
from flask import current_app, g
from sqlalchemy import text
from app import db

# ---------------------------------------------------------------------------
# Cache backend — Redis with automatic in-memory fallback
# ---------------------------------------------------------------------------

_redis_client = None
_redis_available = False


def _get_redis():
    """Return a live Redis client, or None if unavailable."""
    global _redis_client, _redis_available
    if _redis_client is not None:
        return _redis_client if _redis_available else None

    redis_url = os.environ.get("REDIS_URL", "")
    if not redis_url:
        _redis_available = False
        return None

    try:
        import redis
        client = redis.Redis.from_url(redis_url, socket_connect_timeout=1, socket_timeout=1)
        client.ping()
        _redis_client = client
        _redis_available = True
        logging.info("Cache: Redis connecté (%s)", redis_url)
    except Exception as exc:
        logging.warning("Cache: Redis indisponible (%s) — fallback mémoire actif", exc)
        _redis_client = None
        _redis_available = False

    return _redis_client if _redis_available else None


# In-memory fallback storage
_cache: dict = {}
_cache_ttl: dict = {}


def _mem_get(key: str):
    if key in _cache and time.time() < _cache_ttl.get(key, 0):
        return _cache[key]
    return None


def _mem_set(key: str, value, ttl: int):
    _cache[key] = value
    _cache_ttl[key] = time.time() + ttl


def _mem_delete(key: str):
    _cache.pop(key, None)
    _cache_ttl.pop(key, None)


def cache_get(key: str):
    """Get a value from Redis (if available) or in-memory cache."""
    r = _get_redis()
    if r is not None:
        try:
            raw = r.get(key)
            if raw is not None:
                return pickle.loads(raw)
            return None
        except Exception as exc:
            logging.warning("cache_get Redis error: %s — falling back to memory", exc)

    return _mem_get(key)


def cache_set(key: str, value, ttl: int = 300):
    """Store a value in Redis (if available) or in-memory cache."""
    r = _get_redis()
    if r is not None:
        try:
            r.setex(key, ttl, pickle.dumps(value))
            return
        except Exception as exc:
            logging.warning("cache_set Redis error: %s — falling back to memory", exc)

    _mem_set(key, value, ttl)


def cache_delete(key: str):
    """Delete a key from both backends."""
    r = _get_redis()
    if r is not None:
        try:
            r.delete(key)
        except Exception:
            pass
    _mem_delete(key)


def cache_result(ttl=300):
    """Caching decorator — uses Redis when available, in-memory otherwise."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"gec:{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
            cached = cache_get(cache_key)
            if cached is not None:
                return cached
            result = func(*args, **kwargs)
            cache_set(cache_key, result, ttl)
            return result
        return wrapper
    return decorator


def clear_cache():
    """Clear all cached results from both backends."""
    global _cache, _cache_ttl
    r = _get_redis()
    if r is not None:
        try:
            # Only flush keys with our prefix to avoid nuking unrelated data
            for k in r.scan_iter("gec:*"):
                r.delete(k)
        except Exception as exc:
            logging.warning("clear_cache Redis error: %s", exc)
    _cache.clear()
    _cache_ttl.clear()


def clean_expired_cache():
    """Remove expired in-memory cache entries (Redis handles TTL natively)."""
    current_time = time.time()
    expired_keys = [k for k, exp in _cache_ttl.items() if current_time >= exp]
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
        'total_courriers': Courrier.query.filter(Courrier.is_deleted == False).count(),
        'courriers_today': Courrier.query.filter(
            Courrier.is_deleted == False,
            Courrier.date_enregistrement >= today
        ).count(),
        'courriers_this_week': Courrier.query.filter(
            Courrier.is_deleted == False,
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
        execution_time = time.time() - (self.start_time or 0)
        
        # Log performance metrics
        current_app.logger.info(
            f"Performance: {self.operation_name} completed in {execution_time:.3f}s"
        )
        
        # Log slow operations
        if execution_time > 2.0:
            current_app.logger.warning(
                f"Slow operation: {self.operation_name} took {execution_time:.3f}s"
            )