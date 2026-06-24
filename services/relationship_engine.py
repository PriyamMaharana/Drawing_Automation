import networkx as nx
import logging
import math
import cv2
import numpy as np

logger = logging.getLogger(__name__)

class GraphBasedRelationshipEngine:
    """
    Layer 5.5: Graph-Based Relationship Engine (Critical)
    Builds a NetworkX directed graph linking Dimensions -> Leaders -> Geometry.
    """
    def __init__(self):
        self.graph = nx.DiGraph()

    def build_graph(self, dimensions: list, leader_lines: list, geometries: list):
        """
        dimensions: list of dicts/objects representing extracted text dimensions (with bbox/centroid).
        leader_lines: list of lines (e.g. [[x1,y1,x2,y2], ...]) found via OpenCV line detection.
        geometries: list of shapes (arcs, lines, contours) representing the CAD geometry.
        """
        self.graph.clear()
        
        # 1. Add nodes
        for i, dim in enumerate(dimensions):
            self.graph.add_node(f"DIM_{i}", type="dimension", data=dim)
            
        for i, leader in enumerate(leader_lines):
            self.graph.add_node(f"LEADER_{i}", type="leader", data=leader)
            
        for i, geom in enumerate(geometries):
            self.graph.add_node(f"GEOM_{i}", type="geometry", data=geom)

        # 2. Ray-cast from Dimension text to the nearest Leader endpoint
        for i, dim in enumerate(dimensions):
            dim_center = self._get_center(dim)
            best_leader = None
            best_dist = float('inf')
            
            for j, leader in enumerate(leader_lines):
                # Check distance to both endpoints of the leader line
                p1 = (leader[0], leader[1])
                p2 = (leader[2], leader[3])
                
                dist1 = self._euclidean_distance(dim_center, p1)
                dist2 = self._euclidean_distance(dim_center, p2)
                
                min_dist = min(dist1, dist2)
                if min_dist < best_dist and min_dist < 100: # Threshold for connection
                    best_dist = min_dist
                    best_leader = j
                    
            if best_leader is not None:
                self.graph.add_edge(f"DIM_{i}", f"LEADER_{best_leader}", relationship="points_to")
                logger.debug(f"Edge established: DIM_{i} -> LEADER_{best_leader}")

        # 3. Ray-cast from the Leader's opposite endpoint to intersecting Geometry
        for j, leader in enumerate(leader_lines):
            # Check if this leader is connected to a dimension
            connected_dims = [u for u, v in self.graph.in_edges(f"LEADER_{j}")]
            if not connected_dims:
                continue
                
            # Find which endpoint is closer to the dimension to use the other one for geometry
            dim_node = self.graph.nodes[connected_dims[0]]['data']
            dim_center = self._get_center(dim_node)
            
            p1 = (leader[0], leader[1])
            p2 = (leader[2], leader[3])
            
            dist1 = self._euclidean_distance(dim_center, p1)
            dist2 = self._euclidean_distance(dim_center, p2)
            
            # The endpoint farthest from dimension is the one pointing to geometry
            target_pt = p2 if dist1 < dist2 else p1
            
            best_geom = None
            best_dist = float('inf')
            
            for k, geom in enumerate(geometries):
                geom_center = self._get_center(geom)
                dist = self._euclidean_distance(target_pt, geom_center)
                if dist < best_dist and dist < 150: # Threshold
                    best_dist = dist
                    best_geom = k
                    
            if best_geom is not None:
                self.graph.add_edge(f"LEADER_{j}", f"GEOM_{best_geom}", relationship="describes")
                logger.debug(f"Edge established: LEADER_{j} -> GEOM_{best_geom}")

        return self.graph

    def _get_center(self, item) -> tuple:
        # Helper to extract center coordinates from various formats
        if isinstance(item, dict):
            if "bbox" in item:
                bx = item["bbox"]
                return ((bx[0]+bx[2])/2, (bx[1]+bx[3])/2)
            if "center" in item:
                return item["center"]
        elif hasattr(item, "bbox"):
            bx = item.bbox
            if isinstance(bx, tuple) or isinstance(bx, list):
                return ((bx[0]+bx[2])/2, (bx[1]+bx[3])/2)
            return ((bx.x0+bx.x1)/2, (bx.y0+bx.y1)/2)
        elif isinstance(item, list) and len(item) == 4:
            # Assuming a line [x1, y1, x2, y2]
            return ((item[0]+item[2])/2, (item[1]+item[3])/2)
            
        return (0, 0)

    def _euclidean_distance(self, p1: tuple, p2: tuple) -> float:
        return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
