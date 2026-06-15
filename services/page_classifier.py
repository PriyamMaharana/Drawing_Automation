from core.entities.page_profiler import PageProfile


class PageClassifier:

    DRAWING_THRESHOLD = 40

    def classify(
        self,
        page,
        score,
        engineering_symbol_count,
        health_status,
        page_number
    ):

        vector_count = len(page.get_drawings())

        text_count = len(page.get_text("words"))

        page_type = self._page_type(
            score,
            vector_count,
            text_count,
            engineering_symbol_count
        )

        return PageProfile(
            page_number=page_number,
            score=score,
            page_type=page_type,
            vector_count=vector_count,
            text_count=text_count,
            engineering_symbol_count=engineering_symbol_count,
            health_status=health_status,
            is_drawing_page=score >= self.DRAWING_THRESHOLD
        )

    def _page_type(
        self,
        score,
        vector_count,
        text_count,
        symbol_count
    ):

        if score < 0:
            return "DOCUMENT"

        if vector_count > 500 and symbol_count > 2:
            return "DRAWING"

        if text_count > 1000:
            return "NOTES"

        return "MIXED"