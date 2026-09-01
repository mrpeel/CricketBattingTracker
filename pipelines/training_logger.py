#!/usr/bin/env python3
"""
pipelines/training_logger.py — Persistent Dual-Stream Run Logger for ML Pipelines

Captures all stdout and stderr output in real-time without buffering, mirroring
terminal prints directly into timestamped log files in `pipelines/training_logs/`.
Also updates `latest_{prefix}.log` and `latest.log` for easy access.
"""

import os
import sys
import atexit
import datetime
import shutil

class TeeStream:
    """
    Multiplexes writes to both the original stream (terminal stdout/stderr)
    and a log file object, with immediate unbuffered flushing.
    """
    def __init__(self, original_stream, log_file):
        self.original_stream = original_stream
        self.log_file = log_file

    def write(self, message):
        self.original_stream.write(message)
        if self.log_file and not self.log_file.closed:
            self.log_file.write(message)
            self.log_file.flush()

    def flush(self):
        self.original_stream.flush()
        if self.log_file and not self.log_file.closed:
            self.log_file.flush()

    def isatty(self):
        return getattr(self.original_stream, "isatty", lambda: False)()

    def fileno(self):
        return self.original_stream.fileno()


class TrainingLogger:
    """
    Manages active session logging, stream redirection, metadata headers,
    and completion footers.
    """
    def __init__(self, prefix="training", log_dir=None):
        self.prefix = prefix
        self.start_time = datetime.datetime.now()
        timestamp_str = self.start_time.strftime("%Y-%m-%d_%H-%M-%S")
        
        if log_dir is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            log_dir = os.path.join(base_dir, "training_logs")
            
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        
        self.log_filename = f"{prefix}_{timestamp_str}.log"
        self.log_path = os.path.join(self.log_dir, self.log_filename)
        self.latest_prefix_path = os.path.join(self.log_dir, f"latest_{prefix}.log")
        self.latest_path = os.path.join(self.log_dir, "latest.log")
        
        self.log_file = open(self.log_path, "w", encoding="utf-8")
        
        self.orig_stdout = sys.stdout
        self.orig_stderr = sys.stderr
        
        sys.stdout = TeeStream(self.orig_stdout, self.log_file)
        sys.stderr = TeeStream(self.orig_stderr, self.log_file)
        
        self._write_header()
        atexit.register(self.close)

    def _write_header(self):
        print(f"====================================================================================================")
        print(f"  PITCH ANALYTIX PRO — PERSISTENT RUN LOG")
        print(f"  Session Log File : {self.log_path}")
        print(f"  Start Time       : {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Command Line     : {' '.join(sys.argv)}")
        print(f"  Python Version   : {sys.version.split()[0]} ({sys.executable})")
        print(f"====================================================================================================\n", flush=True)

    def close(self):
        if not self.log_file.closed:
            end_time = datetime.datetime.now()
            duration = end_time - self.start_time
            print(f"\n====================================================================================================")
            print(f"  RUN COMPLETED: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  Total Duration: {duration}")
            print(f"  Log Saved to  : {self.log_path}")
            print(f"====================================================================================================", flush=True)
            
            self.log_file.flush()
            self.log_file.close()
            
            # Copy to latest aliases
            try:
                shutil.copyfile(self.log_path, self.latest_prefix_path)
                shutil.copyfile(self.log_path, self.latest_path)
            except Exception:
                pass
            
            sys.stdout = self.orig_stdout
            sys.stderr = self.orig_stderr


def setup_training_logger(prefix="master_retraining", log_dir=None):
    """
    Convenience factory to instantiate and activate a persistent TrainingLogger.
    Returns the logger instance.
    """
    logger = TrainingLogger(prefix=prefix, log_dir=log_dir)
    return logger
