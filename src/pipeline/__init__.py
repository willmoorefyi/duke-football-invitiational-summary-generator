"""
Fantasy Football Pipeline Package

This package contains the pipeline orchestration and stage implementations
for processing fantasy football data from ESPN through to HTML deployment on S3.
"""

from .orchestrator import PipelineOrchestrator
from .stages import PipelineStage, ExtractStage, UploadStage, AggregateStage, DeployStage

__all__ = [
    'PipelineOrchestrator',
    'PipelineStage',
    'ExtractStage',
    'UploadStage',
    'AggregateStage',
    'DeployStage'
]