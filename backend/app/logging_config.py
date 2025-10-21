"""
Logging configuration for DeepCite
"""
import os
import logging
import logging.config
import time
import threading
import functools
from datetime import datetime
import logging.handlers

# Thread-local storage for request context
local = threading.local()

class RequestContextFilter(logging.Filter):
    """Filter to add request context information to log records"""

    def filter(self, record):
        # Add request ID if available
        if hasattr(local, 'request_id'):
            record.request_id = local.request_id
        else:
            record.request_id = 'N/A'

        # Add duration if available
        if hasattr(local, 'start_time'):
            record.duration_ms = int((time.time() - local.start_time) * 1000)
        else:
            record.duration_ms = 0

        return True

def set_request_context(request_id: str):
    """Set request context for the current thread"""
    local.request_id = request_id
    local.start_time = time.time()

def clear_request_context():
    """Clear request context for the current thread"""
    if hasattr(local, 'request_id'):
        delattr(local, 'request_id')
    if hasattr(local, 'start_time'):
        delattr(local, 'start_time')

def timing_logger(logger_name: str = None):
    """Decorator to log execution time of functions"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            logger = logging.getLogger(logger_name or func.__module__)

            logger.info(f"TIMING_START: {func.__name__}")

            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.info(f"TIMING_SUCCESS: {func.__name__} completed in {execution_time:.3f}s")
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"TIMING_ERROR: {func.__name__} failed after {execution_time:.3f}s - {str(e)}")
                raise

        return wrapper
    return decorator

def create_request_middleware(app):
    """Create Flask middleware for request context logging"""

    @app.before_request
    def before_request():
        import uuid
        from flask import request

        # Generate request ID
        request_id = str(uuid.uuid4())[:8]
        set_request_context(request_id)

        # Log request start
        logger = logging.getLogger('app.requests')
        logger.info(f"REQUEST_START: {request.method} {request.path} - {request.remote_addr}")

    @app.after_request
    def after_request(response):
        # Log request completion
        logger = logging.getLogger('app.requests')
        logger.info(f"REQUEST_END: {response.status_code} - Duration: {getattr(local, 'duration_ms', 0)}ms")

        # Clear request context
        clear_request_context()

        return response

    @app.teardown_request
    def teardown_request(exception):
        if exception:
            logger = logging.getLogger('app.requests')
            logger.error(f"REQUEST_ERROR: {str(exception)}")

        # Clear request context in case after_request wasn't called
        clear_request_context()

    return app

def setup_logging(app):
    """
    Setup comprehensive logging configuration
    """
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(app.instance_path), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Logging configuration
    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'detailed': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s - [%(filename)s:%(lineno)d]',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'simple': {
                'format': '%(asctime)s - %(levelname)s - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'json': {
                'format': '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s", "module": "%(module)s", "function": "%(funcName)s", "line": %(lineno)d}',
                'datefmt': '%Y-%m-%dT%H:%M:%S'
            },
            'enhanced_console': {
                'format': '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'enhanced_detailed': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s - [%(filename)s:%(lineno)d] - %(request_id)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'enhanced_json': {
                'format': '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s", "module": "%(module)s", "function": "%(funcName)s", "line": %(lineno)d, "request_id": "%(request_id)s", "duration_ms": %(duration_ms)d}',
                'datefmt': '%Y-%m-%dT%H:%M:%S'
            }
        },
        'filters': {
            'request_context': {
                '()': RequestContextFilter
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': 'INFO',
                'formatter': 'enhanced_console',
                'filters': ['request_context'],
                'stream': 'ext://sys.stdout'
            },
            'file_info': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'INFO',
                'formatter': 'enhanced_detailed',
                'filters': ['request_context'],
                'filename': os.path.join(log_dir, 'deepcite.log'),
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5,
                'encoding': 'utf8'
            },
            'file_error': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'ERROR',
                'formatter': 'enhanced_detailed',
                'filters': ['request_context'],
                'filename': os.path.join(log_dir, 'deepcite_errors.log'),
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5,
                'encoding': 'utf8'
            },
            'file_requests': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'INFO',
                'formatter': 'enhanced_json',
                'filters': ['request_context'],
                'filename': os.path.join(log_dir, 'requests.log'),
                'maxBytes': 20971520,  # 20MB
                'backupCount': 10,
                'encoding': 'utf8'
            },
            'file_operations': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'INFO',
                'formatter': 'enhanced_json',
                'filters': ['request_context'],
                'filename': os.path.join(log_dir, 'operations.log'),
                'maxBytes': 20971520,  # 20MB
                'backupCount': 10,
                'encoding': 'utf8'
            }
        },
        'loggers': {
            # Root logger
            '': {
                'level': 'INFO',
                'handlers': ['console', 'file_info', 'file_error']
            },
            # Request logging
            'app.requests': {
                'level': 'INFO',
                'handlers': ['console', 'file_requests'],
                'propagate': False
            },
            # Operation logging - disable propagation to avoid duplication
            'app.services': {
                'level': 'INFO',
                'handlers': ['console', 'file_operations'],
                'propagate': False
            },
            'app.repositories': {
                'level': 'INFO',
                'handlers': ['console', 'file_operations'],
                'propagate': False
            },
            # Flask and Werkzeug - disable their default logging
            'werkzeug': {
                'level': 'CRITICAL',
                'handlers': [],
                'propagate': False
            },
            'flask': {
                'level': 'CRITICAL',
                'handlers': [],
                'propagate': False
            },
            # ChromaDB telemetry
            'chromadb': {
                'level': 'WARNING',
                'handlers': [],
                'propagate': False
            },
            'chromadb.telemetry': {
                'level': 'ERROR',
                'handlers': [],
                'propagate': False
            }
        }
    }
    
    # Adjust log levels based on environment
    if app.config.get('FLASK_ENV') == 'development':
        logging_config['loggers']['']['level'] = 'INFO'
        logging_config['handlers']['console']['level'] = 'INFO'
    elif app.config.get('FLASK_ENV') == 'production':
        logging_config['loggers']['']['level'] = 'WARNING'
        logging_config['handlers']['console']['level'] = 'WARNING'
    
    # Force disable Flask's default logging BEFORE applying config
    # This prevents Flask from creating duplicate handlers
    app.logger.handlers.clear()
    app.logger.propagate = False
    app.logger.disabled = False  # Re-enable it so our config can control it
    
    # Disable all existing Flask/Werkzeug loggers
    for logger_name in ['werkzeug', 'flask', 'flask.app']:
        logger_obj = logging.getLogger(logger_name)
        logger_obj.handlers.clear()
        logger_obj.propagate = False
        logger_obj.setLevel(logging.CRITICAL)
        logger_obj.addHandler(logging.NullHandler())

    # Apply logging configuration
    logging.config.dictConfig(logging_config)

    # Apply request middleware
    app = create_request_middleware(app)

    # Disable ChromaDB telemetry logging
    for chromadb_logger_name in ['chromadb', 'chromadb.telemetry', 'chromadb.telemetry.product.posthog']:
        chromadb_logger = logging.getLogger(chromadb_logger_name)
        chromadb_logger.handlers.clear()
        chromadb_logger.addHandler(logging.NullHandler())
        chromadb_logger.setLevel(logging.CRITICAL)
        chromadb_logger.propagate = False

    # Final cleanup - ensure no duplicate handlers exist
    root_logger = logging.getLogger()
    # Remove any duplicate handlers that might have been added by Flask
    seen_handlers = set()
    handlers_to_remove = []
    for handler in root_logger.handlers:
        handler_id = id(handler)
        if handler_id in seen_handlers:
            handlers_to_remove.append(handler)
        else:
            seen_handlers.add(handler_id)
    
    for handler in handlers_to_remove:
        root_logger.removeHandler(handler)

    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info(f"DeepCite logging initialized - Environment: {app.config.get('FLASK_ENV', 'unknown')}")
    logger.info(f"Log directory: {log_dir}")

    return logger