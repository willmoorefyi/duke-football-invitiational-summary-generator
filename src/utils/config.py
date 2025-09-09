import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class ESPNConfig:
    espn_s2: Optional[str] = None
    swid: Optional[str] = None
    
    def __post_init__(self):
        # Override with environment variables if available
        self.espn_s2 = os.getenv('ESPN_S2', self.espn_s2)
        self.swid = os.getenv('SWID', self.swid)


@dataclass
class LeagueConfig:
    league_id: Optional[int] = None
    divisions: list = field(default_factory=lambda: ["East", "West"])
    tiebreakers: list = field(default_factory=lambda: ["head_to_head", "points_for", "points_against"])


@dataclass
class NFLScheduleConfig:
    season_start: str = "2024-09-05"
    regular_season_weeks: int = 18
    playoff_weeks: int = 4


@dataclass
class OutputConfig:
    filename_pattern: str = "fantasy_report_week_{week}_{date}.json"
    pretty_print: bool = True
    include_debug_info: bool = False


@dataclass
class LoggingConfig:
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


@dataclass
class Config:
    espn: ESPNConfig = field(default_factory=ESPNConfig)
    league: LeagueConfig = field(default_factory=LeagueConfig)
    nfl_schedule: NFLScheduleConfig = field(default_factory=NFLScheduleConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)


class ConfigManager:
    def __init__(self, config_path: Optional[Path] = None):
        if config_path is None:
            # Default to config/config.yaml relative to project root
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "config" / "config.yaml"
        
        self.config_path = config_path
        self._config = None
    
    def load_config(self) -> Config:
        """Load configuration from YAML file, secrets file, and environment variables."""
        if self._config is not None:
            return self._config
        
        config_data = {}
        
        # Load from main YAML file if it exists
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                config_data = yaml.safe_load(f) or {}
        
        # Load from secrets file if it exists (check both .yaml and .yml extensions)
        secrets_paths = [
            self.config_path.parent / "secrets.yaml",
            self.config_path.parent / "secrets.yml"
        ]
        
        for secrets_path in secrets_paths:
            if secrets_path.exists():
                with open(secrets_path, 'r') as f:
                    secrets_data = yaml.safe_load(f) or {}
                    # Merge secrets into config_data, with secrets taking precedence
                    self._merge_configs(config_data, secrets_data)
                break  # Use the first secrets file found
        
        # Create config objects with merged data
        espn_data = config_data.get('espn', {})
        league_data = config_data.get('league', {})
        nfl_data = config_data.get('nfl_schedule', {})
        output_data = config_data.get('output', {})
        logging_data = config_data.get('logging', {})
        
        self._config = Config(
            espn=ESPNConfig(**espn_data),
            league=LeagueConfig(**league_data),
            nfl_schedule=NFLScheduleConfig(**nfl_data),
            output=OutputConfig(**output_data),
            logging=LoggingConfig(**logging_data)
        )
        
        return self._config
    
    def _merge_configs(self, base_config: dict, override_config: dict) -> None:
        """
        Recursively merge override_config into base_config.
        Values in override_config take precedence.
        """
        for key, value in override_config.items():
            if key in base_config and isinstance(base_config[key], dict) and isinstance(value, dict):
                self._merge_configs(base_config[key], value)
            else:
                base_config[key] = value
    
    def get_config(self) -> Config:
        """Get the loaded configuration, loading it if necessary."""
        if self._config is None:
            return self.load_config()
        return self._config
    
    def reload_config(self) -> Config:
        """Force reload the configuration from file."""
        self._config = None
        return self.load_config()


# Global config manager instance
config_manager = ConfigManager()


def get_config() -> Config:
    """Convenience function to get the global configuration."""
    return config_manager.get_config()