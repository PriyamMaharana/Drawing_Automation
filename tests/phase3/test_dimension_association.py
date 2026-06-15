import pytest
from services.dimension_service import DimensionService
from core.entities.drawing_view import DrawingView
from core.entities.document import DimensionEntity, BoundingBox, Point

def test_dimension_association():
    service = DimensionService()
    view = DrawingView(id="VIEW_1", page_number=1, bbox=BoundingBox(0,0,10,10), confidence=0.9)
    
    dim = DimensionEntity(
        id="DIM_1", page=1, type="linear", specification="1685", tolerance=None,
        reference_dimension=False, raw_text="1685", bbox=BoundingBox(1,1,2,2), center=Point(1.5,1.5)
    )
    
    assoc = service.associate_dimension(dim, view)
    
    assert assoc["feature"] == "shaft_length"
    assert assoc["value"] == 1685.0
