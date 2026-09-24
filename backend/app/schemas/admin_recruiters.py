from pydantic import BaseModel, EmailStr, Field

class RecruiterCreate(BaseModel):
    full_name: str = Field(min_length=1,max_length=200)
    email: EmailStr
    phone: str | None = Field(default=None,max_length=50)
