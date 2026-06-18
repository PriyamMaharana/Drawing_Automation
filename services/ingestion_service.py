import concurrent.futures
import multiprocessing
import gc
import logging
from pathlib import Path
from typing import List, Callable, Dict, Any

logger = logging.getLogger(__name__)

class ParallelIngestion:
    def __init__(self, reserve_cores: int = 1):
        total_cores = multiprocessing.cpu_count()
        self.workers = max(1, total_cores - reserve_cores)
        logging.info(f"Initialized local ingestion engine. Hijacking {self.workers} CPU cores.")
        
    def _process_single_file_worker(self, payload: dict) -> Dict[str, Any]:
        pdf_path = payload["pdf_path"]
        pipeline_func = payload["pipeline_func"]
        
        try:
            result_data = pipeline_func(pdf_path)
            gc.collect()            
            return {"file": pdf_path.name, "status": "SUCCESS", "data": result_data}
        except Exception as e:
            return {"file": pdf_path.name, "status": "FAILED", "error": str(e)}
    

    def execute_batch_ingestion(self, pdf_paths: List[Path], pipeline_func: Callable, ui_progress_callback: Callable = None):
        results = []
        total_files = len(pdf_paths)
        completed = 0
        
        with concurrent.futures.ProcessPoolExecutor(max_workers=self.workers) as executor:
            future_to_file = {
                executor.submit(self._process_single_file_worker, {"pdf_path": pdf, "pipeline_func": pipeline_func}): pdf
                    for pdf in pdf_paths
            }
            
            for future in concurrent.futures.as_completed(future_to_file):
                completed += 1
                result = future.result()
                results.append(result)
                
                logging.debug(f"Completed {result.get('file')} ({completed}/{total_files})")
                
                if ui_progress_callback:
                    ui_progress_callback(completed, total_files)
                    
        return results
