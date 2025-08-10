"""
Configuration for Extraction Analysis Test System

This file contains configuration settings for the extraction analysis test system.
"""

import os
from typing import Dict, Any

# Default configuration
DEFAULT_CONFIG = {
    # Auto-analysis settings
    "auto_analysis_enabled": True,
    "auto_analysis_async": True,
    
    # Output settings
    "default_output_dir": "extraction_analysis_output",
    "create_timestamped_dirs": True,
    
    # Analysis settings
    "min_confidence_threshold": 0.5,
    "max_failure_entries_to_analyze": 10,
    "top_field_success_rates_count": 5,
    
    # Performance settings
    "analysis_timeout_seconds": 300,  # 5 minutes
    "queue_processing_interval_seconds": 1,
    
    # Logging settings
    "log_level": "INFO",
    "log_to_file": False,
    "log_file_path": "extraction_analysis.log",
    
    # Integration settings
    "auto_integrate_with_api": True,
    "auto_integrate_with_upload": True,
    
    # Report settings
    "generate_summary_report": True,
    "generate_detailed_reports": True,
    "generate_failure_analysis": True,
    "generate_performance_metrics": True,
    
    # Field analysis settings
    "fields_to_analyze": [
        'producer', 'cuvee', 'type', 'vintage', 'price', 'bottle_size',
        'grape_variety', 'country', 'region', 'subregion', 'designation',
        'classification', 'sub_type'
    ],
    
    # Confidence analysis settings
    "confidence_thresholds": {
        "high": 0.8,
        "medium": 0.5,
        "low": 0.3
    }
}


class AnalysisConfig:
    """Configuration class for the extraction analysis system."""
    
    def __init__(self, config_dict: Dict[str, Any] = None):
        """
        Initialize configuration.
        
        Args:
            config_dict: Optional configuration dictionary to override defaults
        """
        self.config = DEFAULT_CONFIG.copy()
        
        if config_dict:
            self.config.update(config_dict)
        
        # Load from environment variables
        self._load_from_env()
    
    def _load_from_env(self):
        """Load configuration from environment variables."""
        env_mappings = {
            "EXTRACTION_ANALYSIS_ENABLED": "auto_analysis_enabled",
            "EXTRACTION_ANALYSIS_ASYNC": "auto_analysis_async",
            "EXTRACTION_ANALYSIS_OUTPUT_DIR": "default_output_dir",
            "EXTRACTION_ANALYSIS_LOG_LEVEL": "log_level",
            "EXTRACTION_ANALYSIS_TIMEOUT": "analysis_timeout_seconds",
        }
        
        for env_var, config_key in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                # Convert string values to appropriate types
                if config_key == "auto_analysis_enabled":
                    self.config[config_key] = env_value.lower() in ("true", "1", "yes")
                elif config_key == "auto_analysis_async":
                    self.config[config_key] = env_value.lower() in ("true", "1", "yes")
                elif config_key == "analysis_timeout_seconds":
                    try:
                        self.config[config_key] = int(env_value)
                    except ValueError:
                        pass
                else:
                    self.config[config_key] = env_value
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set a configuration value."""
        self.config[key] = value
    
    def is_enabled(self) -> bool:
        """Check if auto-analysis is enabled."""
        return self.config.get("auto_analysis_enabled", True)
    
    def is_async(self) -> bool:
        """Check if auto-analysis runs asynchronously."""
        return self.config.get("auto_analysis_async", True)
    
    def get_output_dir(self) -> str:
        """Get the default output directory."""
        return self.config.get("default_output_dir", "extraction_analysis_output")
    
    def get_fields_to_analyze(self) -> list:
        """Get the list of fields to analyze."""
        return self.config.get("fields_to_analyze", [])
    
    def get_confidence_thresholds(self) -> dict:
        """Get confidence thresholds."""
        return self.config.get("confidence_thresholds", {})
    
    def should_generate_report(self, report_type: str) -> bool:
        """Check if a specific report type should be generated."""
        key = f"generate_{report_type}"
        return self.config.get(key, True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return self.config.copy()


# Global configuration instance
_config = None


def get_config() -> AnalysisConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = AnalysisConfig()
    return _config


def load_config(config_dict: Dict[str, Any]) -> AnalysisConfig:
    """Load configuration from dictionary."""
    global _config
    _config = AnalysisConfig(config_dict)
    return _config


def load_config_from_file(config_file: str) -> AnalysisConfig:
    """Load configuration from file."""
    import json
    
    try:
        with open(config_file, 'r') as f:
            config_dict = json.load(f)
        return load_config(config_dict)
    except Exception as e:
        print(f"Warning: Could not load config from {config_file}: {e}")
        return get_config()


def save_config_to_file(config_file: str):
    """Save current configuration to file."""
    import json
    
    config = get_config()
    try:
        with open(config_file, 'w') as f:
            json.dump(config.to_dict(), f, indent=2)
        print(f"Configuration saved to {config_file}")
    except Exception as e:
        print(f"Error saving configuration to {config_file}: {e}")


# Convenience functions for common configuration operations
def enable_auto_analysis():
    """Enable auto-analysis."""
    config = get_config()
    config.set("auto_analysis_enabled", True)


def disable_auto_analysis():
    """Disable auto-analysis."""
    config = get_config()
    config.set("auto_analysis_enabled", False)


def set_async_mode(enabled: bool):
    """Set async mode."""
    config = get_config()
    config.set("auto_analysis_async", enabled)


def set_output_dir(output_dir: str):
    """Set output directory."""
    config = get_config()
    config.set("default_output_dir", output_dir)


def set_log_level(log_level: str):
    """Set log level."""
    config = get_config()
    config.set("log_level", log_level)


def get_config_summary() -> Dict[str, Any]:
    """Get a summary of the current configuration."""
    config = get_config()
    return {
        "auto_analysis_enabled": config.is_enabled(),
        "auto_analysis_async": config.is_async(),
        "output_dir": config.get_output_dir(),
        "log_level": config.get("log_level"),
        "timeout_seconds": config.get("analysis_timeout_seconds"),
        "fields_to_analyze_count": len(config.get_fields_to_analyze())
    }


if __name__ == "__main__":
    # Test configuration
    print("Extraction Analysis Test System - Configuration")
    print("=" * 50)
    
    # Test default configuration
    config = get_config()
    print("Default configuration:")
    for key, value in config.to_dict().items():
        print(f"  {key}: {value}")
    
    # Test configuration summary
    print("\nConfiguration summary:")
    summary = get_config_summary()
    for key, value in summary.items():
        print(f"  {key}: {value}")
    
    # Test configuration modification
    print("\nTesting configuration modification...")
    enable_auto_analysis()
    set_async_mode(False)
    set_output_dir("custom_output")
    
    print("Modified configuration summary:")
    summary = get_config_summary()
    for key, value in summary.items():
        print(f"  {key}: {value}")
    
    print("\nConfiguration test completed!") 