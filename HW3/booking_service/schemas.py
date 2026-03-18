from pydantic import BaseModel, EmailStr

class BookingCreate(BaseModel):
    user_id: int
    flight_id: int
    passenger_name: str
    passenger_email: EmailStr
    seat_count: int

class BookingResponse(BaseModel):
    id: int
    user_id: int
    flight_id: int
    passenger_name: str
    passenger_email: str
    seat_count: int
    total_price: float
    status: str
    
    class Config:
        from_attributes = True
