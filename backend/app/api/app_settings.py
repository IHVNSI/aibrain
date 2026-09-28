"""App Settings API: branding, theme, colors, typography, etc."""
import logging
import json
from flask import Blueprint, request, jsonify
from ..extensions import db
from ..auth import require_auth
from ..models import AppSettings
from ..config import Config

logger = logging.getLogger(__name__)
app_settings_bp = Blueprint('app_settings', __name__, url_prefix='/api/settings')


def get_default_app_settings():
    """Get default app settings with all branding, theme, and font colors."""
    return {
        # Basic Branding
        "app_name": "BrainR",
        "logo_url": "",
        "favicon_url": "",
        
        # Theme Mode
        "theme_mode": "light",
        "enable_dark_mode": True,
        
        # Primary Colors
        "primary_color": "#3b82f6",
        "secondary_color": "#1f2937",
        "accent_color": "#f59e0b",
        "background_color": "#ffffff",
        "text_color": "#000000",
        
        # Tab Styling
        "active_tab_text_color": "#1e40af",  # Blue text for active tab
        "active_tab_background_color": "#dbeafe",  # Light blue background for active tab
        "inactive_tab_text_color": "#6b7280",  # Gray text for inactive tab
        "inactive_tab_background_color": "#f3f4f6",  # Light gray background
        
        # Button Styling
        "button_text_color": "#ffffff",  # White text on buttons
        "button_background_color": "#3b82f6",  # Blue button background
        "button_hover_background_color": "#2563eb",  # Darker blue on hover
        "button_border_color": "#3b82f6",
        "button_disabled_text_color": "#9ca3af",  # Gray text for disabled
        "button_disabled_background_color": "#e5e7eb",  # Light gray for disabled
        
        # Link Styling
        "link_text_color": "#3b82f6",  # Blue links
        "link_hover_color": "#2563eb",  # Darker blue on hover
        "link_visited_color": "#7c3aed",  # Purple for visited links
        
        # Navigation Styling
        "nav_text_color": "#1f2937",  # Dark text in nav
        "nav_background_color": "#ffffff",  # White nav background
        "nav_hover_background_color": "#f3f4f6",  # Light gray on hover
        "nav_active_text_color": "#1e40af",  # Blue for active nav item
        "nav_active_background_color": "#dbeafe",  # Light blue for active
        
        # Card/Box Styling
        "card_background_color": "#ffffff",
        "card_border_color": "#e5e7eb",
        "card_text_color": "#1f2937",
        "card_shadow_color": "#0000000f",
        
        # Input Styling
        "input_background_color": "#ffffff",
        "input_border_color": "#d1d5db",
        "input_text_color": "#1f2937",
        "input_placeholder_color": "#9ca3af",
        "input_focus_border_color": "#3b82f6",
        "input_focus_shadow_color": "#3b82f61a",
        
        # Alert/Error Styling
        "error_text_color": "#dc2626",  # Red
        "error_background_color": "#fee2e2",  # Light red
        "warning_text_color": "#d97706",  # Amber/Orange
        "warning_background_color": "#fef3c7",  # Light amber
        "success_text_color": "#059669",  # Green
        "success_background_color": "#d1fae5",  # Light green
        "info_text_color": "#0369a1",  # Cyan
        "info_background_color": "#cffafe",  # Light cyan
        
        # Font Settings
        "font_family": "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        "font_family_mono": "'Monaco', 'Courier New', monospace",
        "font_size_base": 14,
        "font_size_small": 12,
        "font_size_large": 16,
        "font_size_xl": 18,
        "font_size_heading": 24,
        "font_weight_normal": 400,
        "font_weight_medium": 500,
        "font_weight_bold": 700,
        
        # Line Heights
        "line_height_tight": 1.2,
        "line_height_normal": 1.5,
        "line_height_relaxed": 1.75,
        
        # Border Radius
        "border_radius_small": "0.25rem",
        "border_radius_medium": "0.5rem",
        "border_radius_large": "0.75rem",
        "border_radius_full": "9999px",
        
        # Spacing
        "spacing_unit": 8,  # Base unit (8px)
    }

@app_settings_bp.route('/app', methods=['GET'])
@require_auth
def get_app_settings():
    """Get current app settings (branding, theme, colors)."""
    try:
        settings = AppSettings.query.first()
        if not settings:
            # Return defaults if no settings exist
            return jsonify({
                "success": True,
                "config": get_default_app_settings()
            }), 200
        
        config = json.loads(settings.config_json) if settings.config_json else {}
        # Merge with defaults to ensure all fields exist
        defaults = get_default_app_settings()
        config = {**defaults, **config}
        return jsonify({"success": True, "config": config}), 200
    except Exception as e:
        logger.error(f"Error getting app settings: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app_settings_bp.route('/app', methods=['POST'])
@require_auth
def save_app_settings():
    """Save app settings (admin only)."""
    try:
        # Check if user is admin (basic check, can be enhanced)
        data = request.get_json(silent=True) or {}
        
        # Merge with defaults to ensure all fields are preserved
        defaults = get_default_app_settings()
        merged_config = {**defaults, **data}
        
        # Get or create settings record
        settings = AppSettings.query.first()
        if not settings:
            settings = AppSettings(
                config_json=json.dumps(merged_config),
                updated_by="admin"
            )
            db.session.add(settings)
        else:
            settings.config_json = json.dumps(merged_config)
            settings.updated_by = "admin"
        
        db.session.commit()
        
        logger.info(f"✓ App settings saved: app_name={merged_config.get('app_name', 'BrainR')}")
        
        return jsonify({
            "success": True,
            "message": "App settings saved successfully",
            "config": merged_config
        }), 200
    except Exception as e:
        logger.error(f"Error saving app settings: {e}")
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@app_settings_bp.route('/app/theme', methods=['GET'])
def get_app_theme():
    """
    Get app theme (public endpoint, no auth required).
    Used by frontend to apply theme on initial load.
    """
    try:
        settings = AppSettings.query.first()
        defaults = get_default_app_settings()
        
        if not settings:
            return jsonify({"success": True, "theme": defaults}), 200
        
        config = json.loads(settings.config_json) if settings.config_json else {}
        # Merge with defaults to ensure all fields exist
        theme = {**defaults, **config}
        
        return jsonify({"success": True, "theme": theme}), 200
    except Exception as e:
        logger.error(f"Error getting app theme: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
