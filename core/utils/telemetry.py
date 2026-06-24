import logging
import psutil
import time
from typing import Dict

logger = logging.getLogger(__name__)

class TelemetryEngine:
    """
    Layer 14: Telemetry Engine
    Tracks sub-millisecond execution times and RAM footprint to ensure the app
    runs smoothly on legacy factory-floor engineering workstations.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TelemetryEngine, cls).__new__(cls)
            cls._instance.metrics = {}
            cls._instance.start_times = {}
        return cls._instance

    def start_timer(self, metric_name: str):
        self.start_times[metric_name] = time.perf_counter()

    def stop_timer(self, metric_name: str):
        if metric_name in self.start_times:
            elapsed_ms = (time.perf_counter() - self.start_times[metric_name]) * 1000
            self.metrics[metric_name] = round(elapsed_ms, 2)
            del self.start_times[metric_name]

    def record_memory_usage(self):
        process = psutil.Process()
        mem_mb = process.memory_info().rss / (1024 * 1024)
        self.metrics["memory_usage_mb"] = round(mem_mb, 2)
        
        system_mem = psutil.virtual_memory()
        self.metrics["system_ram_percent"] = system_mem.percent

    def get_report(self) -> Dict:
        self.record_memory_usage()
        return self.metrics

    def clear(self):
        self.metrics.clear()
        self.start_times.clear()
        