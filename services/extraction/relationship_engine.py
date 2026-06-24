import logging
import math
import networkx as nx
from typing import List, Dict

logger = logging.getLogger(__name__)

class EngineeringRelationshipEngine:
    """
    Layer 5.5: Graph-Based Relationship Engine
    Constructs a directed graph linking Dimensions to Leader Lines to Target Geometries.
    """
    def __init__(self):
        self.graph = nx.DiGraph()

    def build_graph(self, dimensions: List[Dict], lines: List[Dict], geometries: List[Dict]) -> nx.DiGraph:
        logger.info(f"Building Relationship Graph: {len(dimensions)} Dims, {len(lines)} Leaders.")
        self.graph.clear()
        
        # 1. Add Nodes
        for dim in dimensions:
            node_id = f"DIM_{id(dim)}"
            dim["node_id"] = node_id
            self.graph.add_node(node_id, type="dimension", data=dim)
            
        for line in lines:
            node_id = f"LEADER_{id(line)}"
            line["node_id"] = node_id
            self.graph.add_node(node_id, type="leader", data=line)
            
        for geo in geometries:
            node_id = f"GEO_{id(geo)}"
            geo["node_id"] = node_id
            self.graph.add_node(node_id, type="geometry", data=geo)

        # 2. Establish Edges (Dimension -> Leader)
        self._link_dimensions_to_leaders(dimensions, lines)
        
        # 3. Establish Edges (Leader -> Geometry)
        self._link_leaders_to_geometry(lines, geometries)

        return self.graph

    def _link_dimensions_to_leaders(self, dimensions: List[Dict], lines: List[Dict], max_gap: float = 15.0):
        """Ray-casts from dimension bounding box to nearest leader line endpoints."""
        for dim in dimensions:
            bbox = dim.get("bounding_box_pdf")
            if not bbox: continue
            
            dim_center_x = (bbox[0] + bbox[2]) / 2.0
            dim_center_y = (bbox[1] + bbox[3]) / 2.0
            
            closest_leader = None
            min_dist = float('inf')
            
            for line in lines:
                # line is expected to have [x0, y0, x1, y1] coordinates
                coords = line.get("coords", [0,0,0,0])
                
                # Check distance to both endpoints of the leader line
                dist1 = math.hypot(dim_center_x - coords[0], dim_center_y - coords[1])
                dist2 = math.hypot(dim_center_x - coords[2], dim_center_y - coords[3])
                
                shortest = min(dist1, dist2)
                if shortest < min_dist and shortest <= max_gap:
                    min_dist = shortest
                    closest_leader = line
                    
            if closest_leader:
                conf = 1.0 - (min_dist / max_gap) # Closer = Higher Confidence
                self.graph.add_edge(dim["node_id"], closest_leader["node_id"], relation="controls", confidence=round(conf, 2))
                logger.debug(f"Graph Edge: {dim['node_id']} -> {closest_leader['node_id']} (Conf: {conf:.2f})")

    def _link_leaders_to_geometry(self, lines: List[Dict], geometries: List[Dict], max_gap: float = 5.0):
        """Connects the opposite end of a leader line to a CAD geometry feature."""
        # Note: In a full pipeline, geometries would be extracted via OpenCV contour/Hough Circle mapping.
        pass 
        
    def get_dimension_context(self, dim_node_id: str) -> dict:
        """Traverses the graph to find what geometry a dimension is actually controlling."""
        context = {"leaders": [], "target_geometry": None, "relationship_confidence": 0.0}
        
        if not self.graph.has_node(dim_node_id):
            return context
            
        # Get outgoing edges (Leaders)
        successors = list(self.graph.successors(dim_node_id))
        for succ in successors:
            edge_data = self.graph.get_edge_data(dim_node_id, succ)
            node_data = self.graph.nodes[succ]
            
            if node_data.get("type") == "leader":
                context["leaders"].append(succ)
                context["relationship_confidence"] = edge_data.get("confidence", 0.0)
                
                # Traverse to geometry
                geo_successors = list(self.graph.successors(succ))
                for g_succ in geo_successors:
                    if self.graph.nodes[g_succ].get("type") == "geometry":
                        context["target_geometry"] = g_succ
                        break # Found the primary target
                        
        return context
    