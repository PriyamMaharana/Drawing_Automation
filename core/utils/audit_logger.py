import logging
import math
from typing import List, Dict

logger = logging.getLogger(__name__)

class AdaptiveBalloonEngine:
    """
    Layer 10: Adaptive Balloon Engine (Convergence-Based Solver)
    Uses Force-Directed physics to place balloon markers so they never overlap
    and remain attached to their target bounding boxes via spring forces.
    """
    
    def __init__(self, balloon_radius: float = 12.0, padding: float = 4.0):
        self.radius = balloon_radius
        self.padding = padding
        self.repulsion_force = 200.0
        self.spring_constant = 0.1
        self.damping = 0.7

    def calculate_positions(self, dimensions: List[Dict], max_iterations: int = 100) -> List[Dict]:
        logger.info(f"Igniting Convergence-Based Balloon Solver for {len(dimensions)} items...")
        
        balloons = []
        
        # 1. Initialize balloon starting positions (Top-Left of their bounding boxes)
        for dim in dimensions:
            bbox = dim.get("bounding_box_pdf", [0, 0, 0, 0])
            if bbox == [0, 0, 0, 0]:
                continue
                
            # Start slightly up and left of the dimension text
            start_x = bbox[0] - self.radius
            start_y = bbox[1] - self.radius
            
            balloons.append({
                "dim_ref": dim,
                "x": start_x,
                "y": start_y,
                "anchor_x": bbox[0], # The point it wants to stay near
                "anchor_y": bbox[1],
                "vx": 0.0,
                "vy": 0.0
            })

        # 2. Physics Loop (Force-Directed Graph)
        for iteration in range(max_iterations):
            max_movement = 0.0
            
            # Calculate Repulsion (Balloons pushing away from each other)
            for i, b1 in enumerate(balloons):
                fx, fy = 0.0, 0.0
                
                for j, b2 in enumerate(balloons):
                    if i == j: continue
                    
                    dx = b1["x"] - b2["x"]
                    dy = b1["y"] - b2["y"]
                    dist = math.hypot(dx, dy)
                    min_dist = (self.radius * 2) + self.padding
                    
                    if dist < min_dist and dist > 0.01:
                        # Overlap detected, apply repulsion
                        force = self.repulsion_force * (1.0 - (dist / min_dist))
                        fx += (dx / dist) * force
                        fy += (dy / dist) * force

                # Calculate Attraction (Spring pulling balloon back to its anchor)
                adx = b1["anchor_x"] - b1["x"]
                ady = b1["anchor_y"] - b1["y"]
                fx += adx * self.spring_constant
                fy += ady * self.spring_constant

                # Update Velocity & Position
                b1["vx"] = (b1["vx"] + fx) * self.damping
                b1["vy"] = (b1["vy"] + fy) * self.damping
                
                b1["x"] += b1["vx"]
                b1["y"] += b1["vy"]
                
                movement = math.hypot(b1["vx"], b1["vy"])
                max_movement = max(max_movement, movement)

            # 3. Stop Condition: Convergence Reached
            if max_movement < 0.5:
                logger.debug(f"Physics converged early at iteration {iteration}.")
                break
                
        # 4. Apply Final Computed Coordinates
        for b in balloons:
            b["dim_ref"]["balloon_x"] = round(b["x"], 2)
            b["dim_ref"]["balloon_y"] = round(b["y"], 2)
            
        return dimensions
    