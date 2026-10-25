from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator

class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=128)

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str

class ComponentCreate(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=120,
        description="Required component name",
    )
    category: str = Field(
        min_length=1,
        max_length=80,
        description="Required component category",
    )
    quantity: int = Field(
        ge=0,
        description="Quantity must be zero or greater",
    )
    unit_price: float = Field(
        ge=0,
        description="Unit price must be zero or greater",
    )
    supplier: str = Field(
        min_length=1,
        max_length=120,
        description="Required supplier name",
    )
    reorder_level: int = Field(default=5, ge=0)
    image_url: str | None = Field(default=None, max_length=500)

    @field_validator("image_url")
    @classmethod
    def validate_image_url(cls, value: str | None) -> str | None:
        if value is not None:
            raise ValueError(
                "Image URLs must be assigned through the image upload endpoint."
            )
        return None


    @field_validator("name", "category", "supplier")
    @classmethod
    def trim_text(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("This field is required and cannot be blank.")

        return value

    
class ComponentUpdate(BaseModel):
    quantity: int | None = Field(default=None, ge=0)
    unit_price: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    supplier: str | None = Field(default=None, min_length=1, max_length=120)
    reorder_level: int | None = Field(default=None, ge=0)

    @field_validator("supplier")
    @classmethod
    def trim_supplier(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Supplier cannot be blank")
        return value

class ComponentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sku: str
    name: str
    category: str
    quantity: int
    unit_price: float
    supplier: str
    reorder_level: int
    image_url: str | None
    active: bool
    created_at: datetime | None = None

class AvailabilityResponse(ComponentResponse):
    status: str

class CategoryStockSummary(BaseModel):
    category: str
    quantity: int
    component_count: int

class StockTrendPoint(BaseModel):
    date: str
    quantity: int
    component_count: int

class DashboardResponse(BaseModel):
    total_components: int
    total_stock_value: float
    low_stock_count: int
    low_stock_components: list[ComponentResponse]
    recently_added: list[ComponentResponse]
    category_stock: list[CategoryStockSummary]
    stock_trend: list[StockTrendPoint]
