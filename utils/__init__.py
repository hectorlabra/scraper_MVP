"""
Utility modules for ScraperMVP application.

This package contains various utility modules for the ScraperMVP application,
including helpers for logging, monitoring, notifications, and retry logic.
"""

from utils.helpers import (
    get_random_user_agent, rate_limit, detect_captcha, 
    get_proxy_settings, load_config_from_env, setup_logger
)

# Import newer utility modules when available
try:
    from utils.logging_utils import setup_advanced_logger
except ImportError:
    pass

try:
    from utils.monitoring import (
        metrics_registry, system_monitor, scraper_metrics,
        initialize_monitoring, shutdown_monitoring
    )
except ImportError:
    pass

try:
    from utils.notification import (
        notification_manager, configure_notifications_from_env,
        notify, NotificationLevel
    )
except ImportError:
    pass

try:
    from utils.retry import (
        retry, retry_manager, configure_retry_from_env,
        RetryStrategy, CircuitBreaker
    )
except ImportError:
    pass