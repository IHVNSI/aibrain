"""System administration endpoints (restart server, health checks, server logs, etc.)"""
import os
import sys
import threading
import time
from flask import Blueprint, jsonify, request, g
from app.auth import require_auth
from app.log_manager import get_recent_logs, cleanup_old_logs, get_log_stats

system_bp = Blueprint("system", __name__, url_prefix="/api/system")


@system_bp.route("/status", methods=["GET"])
@require_auth
def system_status():
    """Get system status (health check)"""
    try:
        # Admin-only
        if not g.get('user_ctx') or not g.user_ctx.get('is_admin', False):
            return jsonify({"error": "Admin access required"}), 403
        
        return jsonify({
            "status": "ok",
            "pid": os.getpid(),
            "port": os.getenv("PORT", "5001"),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@system_bp.route("/restart", methods=["POST"])
@require_auth
def restart_server():
    """Restart the Flask backend server"""
    try:
        # Admin-only
        if not g.get('user_ctx') or not g.user_ctx.get('is_admin', False):
            return jsonify({"error": "Admin access required"}), 403
        
        # Get current process info
        pid = os.getpid()
        port = os.getenv("PORT", "5001")
        
        # Schedule restart in background thread with delay
        def do_restart():
            time.sleep(1)  # Wait 1 second to let response be sent
            
            # Get the Python executable and command line args
            python_exe = sys.executable
            script = sys.argv[0]
            
            # Restart by replacing current process
            # This will kill the current process and start a new one with same PID eventually
            os.execvp(python_exe, [python_exe, script])
        
        # Start restart in background thread
        restart_thread = threading.Thread(target=do_restart, daemon=True)
        restart_thread.start()
        
        return jsonify({
            "success": True,
            "message": "Server restart initiated",
            "port": port,
            "pid": pid,
            "restart_in_seconds": 2
        }), 200
    
    except Exception as e:
        import logging
        logging.error(f"Error restarting server: {e}")
        return jsonify({"error": str(e)}), 500


@system_bp.route("/logs", methods=["GET"])
@require_auth
def get_server_logs():
    """Get server logs from the last 10 minutes (admin-only)"""
    try:
        # Admin-only
        if not g.get('user_ctx') or not g.user_ctx.get('is_admin', False):
            return jsonify({"error": "Admin access required"}), 403
        
        minutes = request.args.get('minutes', default=10, type=int)
        if minutes < 1:
            minutes = 10
        if minutes > 120:  # Max 2 hours
            minutes = 120
        
        # Clean up old logs first
        cleanup_old_logs(minutes=minutes)
        
        # Get recent logs
        logs = get_recent_logs(minutes=minutes)
        stats = get_log_stats()
        
        return jsonify({
            "success": True,
            "logs": logs,
            "count": len(logs),
            "stats": stats,
            "minutes": minutes,
        }), 200
    
    except Exception as e:
        import logging
        logging.error(f"Error retrieving server logs: {e}")
        return jsonify({"error": str(e)}), 500


@system_bp.route("/logs/stats", methods=["GET"])
@require_auth
def get_logs_stats():
    """Get log file statistics (admin-only)"""
    try:
        # Admin-only
        if not g.get('user_ctx') or not g.user_ctx.get('is_admin', False):
            return jsonify({"error": "Admin access required"}), 403
        
        stats = get_log_stats()
        
        return jsonify({
            "success": True,
            "stats": stats,
        }), 200
    
    except Exception as e:
        import logging
        logging.error(f"Error getting log stats: {e}")
        return jsonify({"error": str(e)}), 500
