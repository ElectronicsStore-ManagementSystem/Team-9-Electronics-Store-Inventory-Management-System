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

    @field_validator("name", "category", "supplier")
    @classmethod
    def trim_text(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("This field is required and cannot be blank.")

        return value

    
class ComponentUpdate(BaseModel):
    quantity: int | None = Field(default=None, ge=0)
    unit_price: float | None = Field(default=None, ge=0)
    supplier: str | None = Field(default=None, min_length=1, max_length=120)
    reorder_level: int | None = Field(default=None, ge=0)

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
    created_at: datetime

class AvailabilityResponse(ComponentResponse):
    status: str

class DashboardResponse(BaseModel):
    total_components: int
    total_stock_value: float
    low_stock_count: int
    recently_added: list[ComponentResponse]
