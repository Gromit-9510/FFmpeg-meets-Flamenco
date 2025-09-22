from __future__ import annotations

import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum, auto

from PySide6.QtCore import QObject, Signal, QThread

from .ffmpeg_cmd import build_ffmpeg_commands
from .runner import FFmpegRunner


class JobStatus(Enum):
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


@dataclass
class EncodingJob:
    input_path: str
    output_path: str
    config_name: str
    settings: Any  # VideoSettings
    status: JobStatus = JobStatus.PENDING
    progress: float = 0.0
    error_message: str = ""
    start_time: Optional[float] = None
    end_time: Optional[float] = None


class MultiEncoderWorker(QObject):
    """Worker thread for sequential encoding."""
    
    # Signals
    job_started = Signal(int)  # job index
    job_progress = Signal(int, float, str)  # job index, progress, message
    job_completed = Signal(int, bool, str)  # job index, success, message
    all_jobs_completed = Signal()
    encoding_started = Signal(int)  # total job count
    encoding_finished = Signal()
    
    def __init__(self, jobs: List[Dict[str, Any]]) -> None:
        super().__init__()
        self.jobs = jobs
        self.encoding_jobs: List[EncodingJob] = []
        self.should_stop = False
        
        # Convert job dictionaries to EncodingJob objects
        for job_data in jobs:
            encoding_job = EncodingJob(
                input_path=job_data['input_path'],
                output_path=job_data['output_path'],
                config_name=job_data['config_name'],
                settings=job_data['settings']
            )
            self.encoding_jobs.append(encoding_job)

    def stop(self) -> None:
        """Stop the encoding process."""
        self.should_stop = True

    def run(self) -> None:
        """Run all encoding jobs sequentially."""
        total_jobs = len(self.encoding_jobs)
        self.encoding_started.emit(total_jobs)
        
        try:
            for i, job in enumerate(self.encoding_jobs):
                if self.should_stop:
                    job.status = JobStatus.CANCELLED
                    continue
                
                # Start job
                job.status = JobStatus.RUNNING
                job.start_time = time.time()
                self.job_started.emit(i)
                
                try:
                    # Create output directory if needed
                    output_path = Path(job.output_path)
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Build FFmpeg commands
                    print(f"[DEBUG] Building FFmpeg commands for job {i+1}")
                    print(f"  Input: {job.input_path}")
                    print(f"  Output: {job.output_path}")
                    print(f"  Settings: {job.settings}")
                    
                    cmds = build_ffmpeg_commands(job.input_path, job.output_path, job.settings)
                    print(f"[DEBUG] Generated {len(cmds)} command(s)")
                    
                    if not cmds:
                        raise Exception("Failed to generate FFmpeg commands")
                    
                    cmd = cmds[-1]  # Single pass or second pass
                    
                    # Create progress callback
                    def progress_callback(progress: float, message: str = "") -> None:
                        job.progress = progress
                        self.job_progress.emit(i, progress, message)
                    
                    # Run FFmpeg
                    runner = FFmpegRunner(on_log=progress_callback)
                    try:
                        exit_code = runner.run(cmd)
                        
                        job.end_time = time.time()
                        
                        if exit_code == 0:
                            job.status = JobStatus.COMPLETED
                            duration = job.end_time - job.start_time
                            self.job_completed.emit(i, True, f"Completed in {duration:.1f}s")
                        else:
                            job.status = JobStatus.FAILED
                            job.error_message = f"FFmpeg exited with code {exit_code}"
                            self.job_completed.emit(i, False, job.error_message)
                    finally:
                        # Clean up runner resources
                        runner.cleanup()
                        
                except Exception as e:
                    job.status = JobStatus.FAILED
                    job.error_message = str(e)
                    job.end_time = time.time()
                    self.job_completed.emit(i, False, job.error_message)
        
        except Exception as e:
            print(f"Multi-encoder error: {e}")
            # Mark remaining jobs as failed
            for i, job in enumerate(self.encoding_jobs):
                if job.status == JobStatus.PENDING:
                    job.status = JobStatus.FAILED
                    job.error_message = f"Multi-encoder error: {e}"
                    self.job_completed.emit(i, False, job.error_message)
        
        finally:
            self.encoding_finished.emit()
            self.all_jobs_completed.emit()


class MultiEncoder(QObject):
    """Main controller for multi-preset encoding."""
    
    # Signals
    job_started = Signal(int, str, str)  # job index, config name, output path
    job_progress = Signal(int, float, str)  # job index, progress, message
    job_completed = Signal(int, bool, str)  # job index, success, message
    all_jobs_completed = Signal()
    encoding_started = Signal(int)  # total job count
    encoding_finished = Signal()
    
    def __init__(self) -> None:
        super().__init__()
        self.worker_thread: Optional[QThread] = None
        self.worker: Optional[MultiEncoderWorker] = None
        self.is_encoding = False

    def start_encoding(self, jobs: List[Dict[str, Any]]) -> None:
        """Start sequential encoding of multiple jobs."""
        if self.is_encoding:
            return
        
        self.is_encoding = True
        
        # Create worker thread
        self.worker_thread = QThread()
        self.worker = MultiEncoderWorker(jobs)
        self.worker.moveToThread(self.worker_thread)
        
        # Connect signals
        self.worker.job_started.connect(self._on_job_started)
        self.worker.job_progress.connect(self._on_job_progress)
        self.worker.job_completed.connect(self._on_job_completed)
        self.worker.encoding_started.connect(self.encoding_started.emit)
        self.worker.encoding_finished.connect(self._on_encoding_finished)
        self.worker.all_jobs_completed.connect(self.all_jobs_completed.emit)
        
        # Start thread
        self.worker_thread.started.connect(self.worker.run)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker_thread.start()

    def stop_encoding(self) -> None:
        """Stop the current encoding process."""
        if self.worker and self.is_encoding:
            self.worker.stop()

    def _on_job_started(self, job_index: int) -> None:
        """Handle job started signal."""
        if self.worker and job_index < len(self.worker.encoding_jobs):
            job = self.worker.encoding_jobs[job_index]
            self.job_started.emit(job_index, job.config_name, job.output_path)

    def _on_job_progress(self, job_index: int, progress: float, message: str) -> None:
        """Handle job progress signal."""
        self.job_progress.emit(job_index, progress, message)

    def _on_job_completed(self, job_index: int, success: bool, message: str) -> None:
        """Handle job completed signal."""
        self.job_completed.emit(job_index, success, message)

    def _on_encoding_finished(self) -> None:
        """Handle encoding finished signal."""
        self.is_encoding = False
        self.encoding_finished.emit()
        
        if self.worker_thread:
            self.worker_thread.quit()
            self.worker_thread.wait()
