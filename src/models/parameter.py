from pydantic import BaseModel, Field
from typing import Optional

class TextParameter(BaseModel):
    text: str = Field(description="The extracted text string")
    x0: float = Field(description="Left coordinate")
    y0: float = Field(description="Top coordinate")
    x1: float = Field(description="Right coordinate")
    y1: float = Field(description="Bottom coordinate")
    page_number: int = Field(description="Page number where the text was found (0-indexed)")
    is_table_data: bool = Field(default=False, description="Flag indicating if the text falls within a table region")
    serial_no: Optional[int] = Field(default=None, description="Serial number assigned for ballooning")
