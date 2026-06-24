import logging
import networkx as nx
from typing import List, Dict

logger = logging.getLogger(__name__)

class DimensionGroupingEngine:
    """
    Layer 5.7: Dimension Grouping Engine
    Scans the Engineering Relationship Graph for dimensions that share target 
    geometries or collinear axes, grouping them for ERP routing.
    """
    
    @staticmethod
    def group_dimensions(relationship_graph: nx.DiGraph, dimensions: List[Dict]) -> List[Dict]:
        logger.info("Executing Dimension Grouping Engine...")
        
        # Track which geometries are targeted by which dimensions
        geometry_to_dims = {}
        
        # 1. Traverse graph to map Dimensions -> Geometries
        for node, data in relationship_graph.nodes(data=True):
            if data.get("type") == "dimension":
                dim_id = node
                
                # Walk down to find target geometries
                successors = list(relationship_graph.successors(dim_id))
                for succ in successors:
                    if relationship_graph.nodes[succ].get("type") == "leader":
                        geo_successors = list(relationship_graph.successors(succ))
                        for g_succ in geo_successors:
                            if relationship_graph.nodes[g_succ].get("type") == "geometry":
                                if g_succ not in geometry_to_dims:
                                    geometry_to_dims[g_succ] = []
                                geometry_to_dims[g_succ].append(dim_id)

        # 2. Assign Group IDs based on shared geometry (e.g., Hole Patterns)
        group_counter = 1
        dim_to_group = {}
        
        for geo_id, dim_list in geometry_to_dims.items():
            if len(dim_list) > 1:
                # Multiple dimensions control this single geometry (e.g., a coordinate & a diameter)
                group_name = f"GRP_{group_counter:03d}"
                for d_id in dim_list:
                    dim_to_group[d_id] = group_name
                group_counter += 1
                logger.debug(f"Created Dimension Group {group_name} containing {len(dim_list)} items.")

        # 3. Apply the group IDs back to the master dictionary
        for dim in dimensions:
            node_id = dim.get("node_id")
            if node_id and node_id in dim_to_group:
                dim["group_id"] = dim_to_group[node_id]
            else:
                dim["group_id"] = None # Standalone dimension
                
        return dimensions
    