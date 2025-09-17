"""
Fantasy Football Pipeline Package

This package contains the pipeline orchestration and stage implementations
for processing fantasy football data from ESPN through to HTML deployment on S3.
"""

from .orchestrator import PipelineOrchestrator
from .base import PipelineStage
from .extract_stage import ExtractStage
from .upload_stage import UploadStage
from .aggregate_stage import AggregateStage
from .generate_stage import GenerateStage
from .deploy_stage import DeployStage

__all__ = [
    'PipelineOrchestrator',
    'PipelineStage',
    'ExtractStage',
    'UploadStage',
    'AggregateStage',
    'GenerateStage',
    'DeployStage'
]