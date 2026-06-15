import pytest
from services.geometry_service import GeometryService
from core.entities.drawing_view import DrawingView
from core.entities.document import BoundingBox

def test_feature_recognition():
    service = GeometryService()
    view = DrawingView(id="VIEW_1", page_number=1, bbox=BoundingBox(0,0,10,10), confidence=0.9)
    
    features = service.recognize_features(view)
    
    assert features["feature"] == "hole"
    assert features["diameter"] == 10
    assert features["quantity"] == 6
