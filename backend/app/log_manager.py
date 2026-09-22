"""Server logs manager - handles log file operations and retrieval"""
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "logs")
LOG_FILE = os.path.join(LOG_DIR, "server.log")


def ensure_log_dir():
    """Ensure logs directory exists"""
    os.makedirs(LOG_DIR, exist_ok=True)


def setup_log_file_handler():
    """Setup file handler for logging to server.log"""
    ensure_log_dir()
    
    # Get root logger
    root_logger = logging.getLogger()
    
    # Check if file handler already exists
    for handler in root_logger.handlers:
        if isinstance(handler, logging.FileHandler) and handler.baseFilename == LOG_FILE:
            return
    
    # Create file handler with UTF-8 encoding for Unicode support
    file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    
    # Add handler to root logger
    root_logger.addHandler(file_handler)


def get_recent_logs(minutes=10):
    """
    Get logs from the last N minutes
    Returns list of log lines with their timestamps
    """
    ensure_log_dir()
    
    if not os.path.exists(LOG_FILE):
        return []
    
    cutoff_time = datetime.now() - timedelta(minutes=minutes)
    logs = []
    
    try:
        with open(LOG_FILE, 'r') as f:
            for line in f:
                # Parse timestamp from log line
                # Format: "2026-07-31 09:27:31,418 ..."
                try:
                    parts = line.split(' ', 2)
                    if len(parts) >= 2:
                        date_str = parts[0]
                        time_str = parts[1]
                        
                        # Parse datetime
                        log_time_str = f"{date_str} {time_str}"
                        # Handle milliseconds in time
                        if ',' in log_time_str:
                            log_time_str = log_time_str.replace(',', '.')
                        
                        log_time = datetime.strptime(log_time_str.split('.')[0], '%Y-%m-%d %H:%M:%S')
                        
                        if log_time >= cutoff_time:
                            logs.append(line.rstrip('\n'))
                except (ValueError, IndexError):
                    # If we can't parse timestamp, include the line
                    logs.append(line.rstrip('\n'))
    except Exception as e:
        logs.append(f"Error reading logs: {e}")
    
    return logs


def cleanup_old_logs(minutes=10):
    """
    Delete log lines older than N minutes
    Rewrites the log file with only recent logs
    """
    ensure_log_dir()
    
    if not os.path.exists(LOG_FILE):
        return
    
    recent_logs = get_recent_logs(minutes=minutes)
    
    try:
        with open(LOG_FILE, 'w') as f:
            for log_line in recent_logs:
                f.write(log_line + '\n')
    except Exception as e:
        logging.error(f"Error cleaning up logs: {e}")


def get_log_stats():
    """Get statistics about the log file"""
    ensure_log_dir()
    
    if not os.path.exists(LOG_FILE):
        return {"total_lines": 0, "file_size": 0, "recent_logs": 0}
    
    stats = {
        "total_lines": 0,
        "file_size": os.path.getsize(LOG_FILE),
        "recent_logs": 0,
        "last_modified": None,
    }
    
    try:
        with open(LOG_FILE, 'r') as f:
            stats["total_lines"] = sum(1 for _ in f)
        
        stats["recent_logs"] = len(get_recent_logs(minutes=10))
        stats["last_modified"] = datetime.fromtimestamp(os.path.getmtime(LOG_FILE)).isoformat()
    except Exception as e:
        logging.error(f"Error getting log stats: {e}")
    
    return stats
