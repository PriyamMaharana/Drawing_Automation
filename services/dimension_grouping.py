import logging
import networkx as nx

logger = logging.getLogger(__name__)

class DimensionGroupingEngine:
    """
    Layer 5.7: Dimension Grouping Engine
    Scans the Relationship Graph for Dimensions sharing the same collinear axis 
    (Baseline/Ordinate routing). Tags them with a shared dimension_group_id.
    """
    def __init__(self):
        pass

    def group_dimensions(self, graph: nx.DiGraph):
        """
        Analyzes the NetworkX graph and assigns group IDs to dimensions that are collinear.
        """
        dimensions = [n for n, d in graph.nodes(data=True) if d.get('type') == 'dimension']
        
        groups = {}
        group_id_counter = 1
        
        # Simple clustering based on X or Y coordinate proximity
        # O(N^2) comparison for demonstration, can use KD-Tree for optimization
        for dim_id in dimensions:
            dim_data = graph.nodes[dim_id]['data']
            center = self._get_center(dim_data)
            
            assigned = False
            for group_id, group_dims in groups.items():
                # Check if it belongs to this group (collinear check)
                # Compare with the first member of the group
                ref_dim_id = group_dims[0]
                ref_dim_data = graph.nodes[ref_dim_id]['data']
                ref_center = self._get_center(ref_dim_data)
                
                # Check if aligned horizontally or vertically (tolerance 5px)
                if abs(center[0] - ref_center[0]) < 5.0 or abs(center[1] - ref_center[1]) < 5.0:
                    groups[group_id].append(dim_id)
                    graph.nodes[dim_id]['dimension_group_id'] = group_id
                    assigned = True
                    break
                    
            if not assigned:
                groups[group_id_counter] = [dim_id]
                graph.nodes[dim_id]['dimension_group_id'] = group_id_counter
                group_id_counter += 1
                
        logger.info(f"Grouped {len(dimensions)} dimensions into {len(groups)} collinear groups.")
        return graph

    def _get_center(self, item) -> tuple:
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
        return (0, 0)
