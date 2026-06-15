import logging
import sys
from pathlib import Path

def setup_3_tier_logging(phase_name: str, project_root: Path):
    """
    Configures the Enterprise 3-Tier Logging Architecture.
    1. Client (INFO+): High-level progress.
    2. Developer (DEBUG+): Granular matrix math and heuristics.
    3. Crash (ERROR+): Full Python tracebacks for Doomsday files.
    """
    log_dir = project_root / "debug" / "logs" / phase_name
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Define File Paths
    client_log = log_dir / "client.log"
    developer_log = log_dir / "developer.log"
    crash_log = log_dir / "crash.log"
    
    # Clear old logs for the new run
    for log_file in [client_log, developer_log, crash_log]:
        if log_file.exists():
            log_file.write_text("")

    # Reset existing handlers (prevents duplicate logs if called twice)
    logger = logging.getLogger()
    if logger.hasHandlers():
        logger.handlers.clear()
        
    logger.setLevel(logging.DEBUG) # Master level
    
    # Formatter
    standard_formatter = logging.Formatter('%(asctime)s - [%(levelname)s] - %(message)s', datefmt='%H:%M:%S')
    error_formatter = logging.Formatter('\n%(asctime)s - [CRITICAL FAULT]\n%(message)s\n', datefmt='%Y-%m-%d %H:%M:%S')

    # 1. Client Handler (INFO & WARNINGS)
    client_handler = logging.FileHandler(client_log, encoding='utf-8')
    client_handler.setLevel(logging.INFO)
    client_handler.setFormatter(standard_formatter)

    # 2. Developer Handler (EVERYTHING)
    dev_handler = logging.FileHandler(developer_log, encoding='utf-8')
    dev_handler.setLevel(logging.DEBUG)
    dev_handler.setFormatter(standard_formatter)

    # 3. Crash Handler (ERRORS & EXCEPTIONS)
    crash_handler = logging.FileHandler(crash_log, encoding='utf-8')
    crash_handler.setLevel(logging.ERROR)
    crash_handler.setFormatter(error_formatter)

    # 4. Console Handler (Keeps your terminal looking clean)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter('%(message)s'))

    # Attach all handlers
    logger.addHandler(client_handler)
    logger.addHandler(dev_handler)
    logger.addHandler(crash_handler)
    logger.addHandler(console_handler)
    
    