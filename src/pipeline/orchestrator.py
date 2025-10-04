"""
Pipeline Orchestrator

Coordinates the execution of all pipeline stages with dependency management,
error handling, and progress tracking.
"""

import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

try:
    from .base import PipelineStage
    from .extract_stage import ExtractStage
    from .upload_stage import UploadStage
    from .aggregate_stage import AggregateStage
    from .generate_stage import GenerateStage
    from .deploy_stage import DeployStage
    from ..utils.config import get_config
except ImportError:
    from base import PipelineStage
    from extract_stage import ExtractStage
    from upload_stage import UploadStage
    from aggregate_stage import AggregateStage
    from generate_stage import GenerateStage
    from deploy_stage import DeployStage
    from utils.config import get_config


class PipelineStatus(Enum):
    """Pipeline execution status"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class PipelineResult:
    """Result of pipeline stage execution"""
    stage_name: str
    status: PipelineStatus
    output_path: Optional[str] = None
    metadata: Dict[str, Any] = None
    error_message: Optional[str] = None
    execution_time: Optional[float] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class PipelineOrchestrator:
    """
    Orchestrates the execution of all pipeline stages with dependency management,
    error handling, rollback capabilities, and progress tracking.
    """

    def __init__(self, league_id: int, year: Optional[int] = None,
                 espn_s2: Optional[str] = None, swid: Optional[str] = None,
                 dry_run: bool = False):
        """
        Initialize the pipeline orchestrator.

        Args:
            league_id: ESPN fantasy league ID
            year: Fantasy season year (defaults to current year)
            espn_s2: ESPN_S2 cookie value (overrides config)
            swid: SWID cookie value (overrides config)
            dry_run: If True, simulate execution without making changes
        """
        self.league_id = league_id
        self.year = year or datetime.now().year
        self.espn_s2 = espn_s2
        self.swid = swid
        self.dry_run = dry_run

        self.config = get_config()
        self.logger = logging.getLogger(__name__)

        # Initialize stages
        self.stages = self._initialize_stages()

        # Execution tracking
        self.execution_id = f"pipeline_{league_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.results: Dict[str, PipelineResult] = {}
        self.current_stage: Optional[str] = None

        self.logger.info(f"Initialized PipelineOrchestrator for league {league_id}, execution ID: {self.execution_id}")

    def _initialize_stages(self) -> Dict[str, PipelineStage]:
        """Initialize all pipeline stages with their dependencies"""
        stages = {}

        # Stage 1: Extract ESPN data
        stages['extract'] = ExtractStage(
            league_id=self.league_id,
            year=self.year,
            espn_s2=self.espn_s2,
            swid=self.swid,
            dry_run=self.dry_run
        )

        # Stage 2: Upload to DynamoDB
        stages['upload'] = UploadStage(
            league_id=self.league_id,
            dry_run=self.dry_run
        )

        # Stage 3: Aggregate data
        stages['aggregate'] = AggregateStage(
            league_id=self.league_id,
            dry_run=self.dry_run
        )

        # Stage 4: Generate HTML
        stages['generate'] = GenerateStage(
            league_id=self.league_id,
            dry_run=self.dry_run
        )

        # Stage 5: Deploy to S3
        stages['deploy'] = DeployStage(
            league_id=self.league_id,
            dry_run=self.dry_run
        )

        return stages

    def run_full_pipeline(self, week: Optional[int] = None,
                         output_dir: Optional[str] = None) -> Dict[str, PipelineResult]:
        """
        Execute all pipeline stages in sequence.

        Args:
            week: Specific week to process (defaults to current week)
            output_dir: Base output directory (defaults to config)

        Returns:
            Dict mapping stage names to their results
        """
        self.logger.info(f"Starting full pipeline execution (ID: {self.execution_id})")

        try:
            # Stage 1: Extract
            extract_result = self.run_stage('extract', week=week, output_dir=output_dir)
            if extract_result.status != PipelineStatus.SUCCESS:
                raise RuntimeError(f"Extract stage failed: {extract_result.error_message}")

            # Stage 2: Aggregate (calculate standings from historical + current data)
            aggregate_result = self.run_stage('aggregate',
                                            current_week_file=extract_result.output_path)
            if aggregate_result.status != PipelineStatus.SUCCESS:
                raise RuntimeError(f"Aggregate stage failed: {aggregate_result.error_message}")

            # Stage 3: Upload (uses enhanced JSON with computed standings)
            upload_result = self.run_stage('upload', input_file=aggregate_result.output_path)
            if upload_result.status != PipelineStatus.SUCCESS:
                raise RuntimeError(f"Upload stage failed: {upload_result.error_message}")

            # Stage 4: Generate HTML (uses enhanced JSON)
            generate_result = self.run_stage('generate', input_file=aggregate_result.output_path)
            if generate_result.status != PipelineStatus.SUCCESS:
                raise RuntimeError(f"Generate stage failed: {generate_result.error_message}")

            # Stage 5: Deploy to S3 (uses HTML file and enhanced JSON for overview)
            deploy_result = self.run_stage('deploy',
                                         input_file=generate_result.output_path,
                                         enhanced_json_path=aggregate_result.output_path)
            if deploy_result.status != PipelineStatus.SUCCESS:
                raise RuntimeError(f"Deploy stage failed: {deploy_result.error_message}")

            self.logger.info(f"Full pipeline execution completed successfully (ID: {self.execution_id})")
            return self.results

        except Exception as e:
            self.logger.error(f"Pipeline execution failed: {e}")
            self._handle_pipeline_failure(str(e))
            raise

    def run_stage(self, stage_name: str, **kwargs) -> PipelineResult:
        """
        Execute a single pipeline stage.

        Args:
            stage_name: Name of the stage to execute
            **kwargs: Stage-specific arguments

        Returns:
            PipelineResult with execution details
        """
        if stage_name not in self.stages:
            raise ValueError(f"Unknown stage: {stage_name}")

        self.current_stage = stage_name
        stage = self.stages[stage_name]

        self.logger.info(f"Starting stage: {stage_name}")
        start_time = datetime.now()

        try:
            # Execute the stage
            output_path, metadata = stage.execute(**kwargs)

            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()

            # Create successful result
            result = PipelineResult(
                stage_name=stage_name,
                status=PipelineStatus.SUCCESS,
                output_path=output_path,
                metadata=metadata,
                execution_time=execution_time
            )

            self.results[stage_name] = result
            self.logger.info(f"Stage {stage_name} completed successfully in {execution_time:.2f}s")

            return result

        except Exception as e:
            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()

            # Create failed result
            result = PipelineResult(
                stage_name=stage_name,
                status=PipelineStatus.FAILED,
                error_message=str(e),
                execution_time=execution_time
            )

            self.results[stage_name] = result
            self.logger.error(f"Stage {stage_name} failed after {execution_time:.2f}s: {e}")

            return result

        finally:
            self.current_stage = None

    def get_pipeline_status(self) -> Dict[str, Any]:
        """
        Get current pipeline execution status.

        Returns:
            Dict with pipeline status information
        """
        return {
            'execution_id': self.execution_id,
            'league_id': self.league_id,
            'year': self.year,
            'current_stage': self.current_stage,
            'dry_run': self.dry_run,
            'stages': {
                stage_name: {
                    'status': result.status.value,
                    'output_path': result.output_path,
                    'execution_time': result.execution_time,
                    'error_message': result.error_message
                }
                for stage_name, result in self.results.items()
            },
            'overall_status': self._get_overall_status()
        }

    def _get_overall_status(self) -> str:
        """Determine overall pipeline status based on stage results"""
        if not self.results:
            return PipelineStatus.PENDING.value

        if self.current_stage:
            return PipelineStatus.RUNNING.value

        failed_stages = [r for r in self.results.values() if r.status == PipelineStatus.FAILED]
        if failed_stages:
            return PipelineStatus.FAILED.value

        # Check if all expected stages completed successfully
        expected_stages = ['extract', 'aggregate', 'upload', 'generate', 'deploy']
        completed_stages = [name for name, result in self.results.items()
                          if result.status == PipelineStatus.SUCCESS]

        if len(completed_stages) == len(expected_stages):
            return PipelineStatus.SUCCESS.value
        else:
            return PipelineStatus.RUNNING.value

    def _handle_pipeline_failure(self, error_message: str):
        """Handle pipeline failure with cleanup and rollback if needed"""
        self.logger.error(f"Pipeline failure detected: {error_message}")

        # TODO: Implement rollback logic for each stage
        # - Remove uploaded DynamoDB records
        # - Clean up temporary files
        # - Revert S3 deployments if needed

        self.current_stage = None

    def save_pipeline_log(self, output_path: Optional[str] = None) -> str:
        """
        Save pipeline execution log to file.

        Args:
            output_path: Path to save log file (defaults to output/logs/)

        Returns:
            Path to saved log file
        """
        if output_path is None:
            log_dir = Path("output/logs")
            log_dir.mkdir(parents=True, exist_ok=True)
            output_path = log_dir / f"pipeline_log_{self.execution_id}.json"
        else:
            output_path = Path(output_path)

        log_data = {
            'execution_id': self.execution_id,
            'timestamp': datetime.now().isoformat(),
            'pipeline_status': self.get_pipeline_status(),
            'stage_results': {
                name: {
                    'status': result.status.value,
                    'output_path': result.output_path,
                    'metadata': result.metadata,
                    'execution_time': result.execution_time,
                    'error_message': result.error_message
                }
                for name, result in self.results.items()
            }
        }

        with open(output_path, 'w') as f:
            json.dump(log_data, f, indent=2, default=str)

        self.logger.info(f"Pipeline log saved to: {output_path}")
        return str(output_path)