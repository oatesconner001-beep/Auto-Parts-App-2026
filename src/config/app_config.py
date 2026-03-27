"""
Application configuration management.

Handles loading, saving, and managing all configuration settings for the Parts Agent.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any

class AppConfig:
    """Centralized configuration management for the Parts Agent."""

    def __init__(self):
        self.config_dir = Path(__file__).parent.parent.parent / "config"
        self.config_file = self.config_dir / "app_settings.json"
        self.site_configs_dir = self.config_dir / "site_configs"

        # Default configuration values
        self.defaults = {
            "ai_backend": "Claude API",
            "cost_limit": 5.00,
            "scraping_delay": 2.5,
            "max_workers": 4,
            "timeout": 45,
            "preferred_models": {
                "claude": "claude-sonnet-4-20250514",
                "gemini": "gemini-3-flash-preview",
                "ollama": "moondream"
            },
            "excel_settings": {
                "auto_save": True,
                "backup_enabled": True,
                "color_coding": True
            },
            "ui_settings": {
                "theme": "default",
                "log_retention": 200,
                "auto_refresh_stats": True
            }
        }

        # Current configuration (starts with defaults)
        self.settings = self.defaults.copy()

        # Ensure config directories exist
        self._ensure_directories()

    def _ensure_directories(self):
        """Ensure configuration directories exist."""
        self.config_dir.mkdir(exist_ok=True)
        self.site_configs_dir.mkdir(exist_ok=True)

    def load(self):
        """Load configuration from file."""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    saved_config = json.load(f)

                # Merge with defaults (preserving any new default keys)
                self.settings = {**self.defaults, **saved_config}
                return True
        except Exception as e:
            print(f"Failed to load config: {e}")
            # Fall back to defaults
            self.settings = self.defaults.copy()

        return False

    def save(self):
        """Save current configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
            return True
        except Exception as e:
            print(f"Failed to save config: {e}")
            return False

    def get(self, key: str, default=None):
        """Get configuration value."""
        keys = key.split('.')
        value = self.settings

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any):
        """Set configuration value."""
        keys = key.split('.')
        target = self.settings

        # Navigate to the parent of the final key
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]

        # Set the final key
        target[keys[-1]] = value

    @property
    def ai_backend(self):
        """Get current AI backend."""
        return self.get("ai_backend", "Claude API")

    @ai_backend.setter
    def ai_backend(self, value):
        """Set AI backend."""
        self.set("ai_backend", value)

    @property
    def cost_limit(self):
        """Get daily cost limit."""
        return self.get("cost_limit", 5.00)

    @cost_limit.setter
    def cost_limit(self, value):
        """Set daily cost limit."""
        self.set("cost_limit", float(value))

    def get_site_configs(self) -> Dict[str, Dict]:
        """Get all site configurations."""
        configs = {}

        try:
            for config_file in self.site_configs_dir.glob("*.json"):
                with open(config_file, 'r') as f:
                    site_name = config_file.stem
                    configs[site_name] = json.load(f)
        except Exception as e:
            print(f"Failed to load site configs: {e}")

        return configs

    def save_site_config(self, site_name: str, config: Dict):
        """Save a site configuration."""
        try:
            config_file = self.site_configs_dir / f"{site_name}.json"
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            print(f"Failed to save site config for {site_name}: {e}")
            return False

    def export_config(self, filepath: str):
        """Export entire configuration to a file."""
        try:
            export_data = {
                "app_settings": self.settings,
                "site_configs": self.get_site_configs()
            }

            with open(filepath, 'w') as f:
                json.dump(export_data, f, indent=2)
            return True
        except Exception as e:
            print(f"Failed to export config: {e}")
            return False

    def import_config(self, filepath: str):
        """Import configuration from a file."""
        try:
            with open(filepath, 'r') as f:
                import_data = json.load(f)

            # Import app settings
            if "app_settings" in import_data:
                self.settings = {**self.defaults, **import_data["app_settings"]}
                self.save()

            # Import site configs
            if "site_configs" in import_data:
                for site_name, config in import_data["site_configs"].items():
                    self.save_site_config(site_name, config)

            return True
        except Exception as e:
            print(f"Failed to import config: {e}")
            return False

    def reset_to_defaults(self):
        """Reset configuration to defaults."""
        self.settings = self.defaults.copy()
        self.save()

    def validate(self):
        """Validate current configuration."""
        errors = []

        # Validate AI backend
        valid_backends = ["Claude API", "Gemini API", "Ollama Local", "Rules Only"]
        if self.ai_backend not in valid_backends:
            errors.append(f"Invalid AI backend: {self.ai_backend}")

        # Validate cost limit
        try:
            cost = float(self.cost_limit)
            if cost < 0:
                errors.append("Cost limit cannot be negative")
        except (TypeError, ValueError):
            errors.append("Cost limit must be a number")

        # Validate scraping delay
        try:
            delay = float(self.get("scraping_delay", 2.5))
            if delay < 0:
                errors.append("Scraping delay cannot be negative")
        except (TypeError, ValueError):
            errors.append("Scraping delay must be a number")

        return errors

    def __str__(self):
        """String representation of configuration."""
        return f"AppConfig(backend={self.ai_backend}, cost_limit=${self.cost_limit})"