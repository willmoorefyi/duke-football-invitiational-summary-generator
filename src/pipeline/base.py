"""
Pipeline Stage Base Class

Defines the abstract base class for all pipeline stages.
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

try:
    from ..utils.config import get_config
except ImportError:
    from utils.config import get_config


class PipelineStage(ABC):
    """
    Abstract base class for all pipeline stages.

    Each stage should implement the execute method to perform its specific
    data processing tasks and return output path and metadata.
    """

    def __init__(self, league_id: int, dry_run: bool = False):
        """
        Initialize the pipeline stage.

        Args:
            league_id: ESPN fantasy league ID
            dry_run: If True, simulate execution without making changes
        """
        self.league_id = league_id
        self.dry_run = dry_run
        self.config = get_config()
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def execute(self, **kwargs) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Execute the stage logic.

        Args:
            **kwargs: Stage-specific arguments

        Returns:
            Tuple of (output_path, metadata)
        """
        pass

    def _ensure_output_directory(self, directory: str) -> Path:
        """Ensure output directory exists"""
        path = Path(directory)
        if not self.dry_run:
            path.mkdir(parents=True, exist_ok=True)
        return path