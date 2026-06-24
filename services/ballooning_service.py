import logging
from typing import List, Dict, Any
import math

logger = logging.getLogger(__name__)

class BallooningService:
    """
    Layer 10: Adaptive Balloon Engine
    Implements a Convergence-Based Solver (Force-Directed) for balloon placement.
    """
    def __init__(self, start_index: int = 1):
        self.current_id = start_index
        self.nodes = [] # Balloon Circles (repel each other)
        self.edges = [] # Leader lines (act as rigid springs to their target)

    def apply_balloons(self, intelligence: list) -> int:
        logger.info("Applying AS9102 FAI Balloons using Force-Directed Adaptive Engine...")
        count = 0
        
        for view in intelligence:
            for dim in view.get("dimensions", []):
                dim["balloon_id"] = self.current_id
                
                # Initialize node for force-directed placement
                # Assume dim has a center or bbox
                target_x, target_y = self._get_center(dim)
                
                # Initial placement slightly offset from target
                node = {
                    "id": self.current_id,
                    "target_x": target_x,
                    "target_y": target_y,
                    "x": target_x + 30,
                    "y": target_y - 30,
                    "radius": 15 # Assuming 15px balloon radius
                }
                self.nodes.append(node)
                
                logger.debug(f"Assigned Balloon ID [{self.current_id}] to feature: '{dim.get('raw_text', '')}'")
                self.current_id += 1
                count += 1

        if count > 0:
            self._converge_balloons()
                
        logger.info(f"Successfully generated {count} continuous inspection balloons with physics convergence.")
        return count

    def _get_center(self, item) -> tuple:
        if isinstance(item, dict):
            if "bbox" in item:
                bx = item["bbox"]
                return ((bx[0]+bx[2])/2, (bx[1]+bx[3])/2)
            if "center" in item:
                return item["center"]
        return (0, 0)

    def _converge_balloons(self, max_iterations: int = 100):
        """
        Force-Directed placement solver.
        - Repulsion between balloon nodes.
        - Spring attraction between balloon and target dimension.
        """
        spring_k = 0.1
        repulsion_k = 1000.0
        
        logger.info(f"Starting force-directed physics solver for {len(self.nodes)} balloons...")
        
        for i in range(max_iterations):
            max_delta = 0.0
            
            for node in self.nodes:
                fx, fy = 0.0, 0.0
                
                # 1. Spring force to target
                dx = node["target_x"] - node["x"]
                dy = node["target_y"] - node["y"]
                dist_to_target = math.sqrt(dx**2 + dy**2)
                
                # We want balloons to rest at a certain distance (e.g., 40px)
                target_dist = 40.0
                if dist_to_target > 0:
                    force = spring_k * (dist_to_target - target_dist)
                    fx += force * (dx / dist_to_target)
                    fy += force * (dy / dist_to_target)
                
                # 2. Repulsion from other balloons
                for other in self.nodes:
                    if node["id"] == other["id"]: continue
                    
                    rx = node["x"] - other["x"]
                    ry = node["y"] - other["y"]
                    r_dist = math.sqrt(rx**2 + ry**2)
                    
                    min_dist = node["radius"] * 2 + 5 # 5px padding
                    if r_dist < min_dist and r_dist > 0:
                        force = repulsion_k / (r_dist ** 2)
                        fx += force * (rx / r_dist)
                        fy += force * (ry / r_dist)
                        
                # Update position
                node["x"] += fx
                node["y"] += fy
                
                delta = math.sqrt(fx**2 + fy**2)
                if delta > max_delta:
                    max_delta = delta
                    
            if max_delta < 1.0: # Stop when delta_movement < 1px
                logger.debug(f"Physics convergence reached in {i+1} iterations.")
                break
                
        else:
            logger.debug(f"Physics solver hit max iterations ({max_iterations}) without full convergence.")