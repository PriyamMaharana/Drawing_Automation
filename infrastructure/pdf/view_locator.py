import logging
from typing import List

from core.entities.drawing_package import DrawingPackage
from core.entities.drawing_view import DrawingView
from core.entities.document import BoundingBox

logger = logging.getLogger(__name__)

class ViewLocator:
    """Phase 1.1: View Locator. Detects geometry views within drawing pages."""

    def __init__(self):
        pass

    def locate_views(self, package: DrawingPackage) -> List[DrawingView]:
        """
        Takes a DrawingPackage and returns a list of DrawingViews.
        """
        views = []
        # Mock logic: Create a main view for each drawing page
        for page in package.drawing_pages:
            view = DrawingView(
                id=f"VIEW_{page.page_number}_MAIN",
                page_number=page.page_number,
                bbox=BoundingBox(0.0, 0.0, package.profile.page_width, package.profile.page_height),
                confidence=0.95
            )
            views.append(view)
        
        return views
