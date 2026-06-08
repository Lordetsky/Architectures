from sqlalchemy import Column, Integer, String, Float, CheckConstraint
from database import Base

class Booking(Base):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    flight_id = Column(Integer, nullable=False)
    passenger_name = Column(String, nullable=False)
    passenger_email = Column(String, nullable=False)
    seat_count = Column(Integer, nullable=False)
    total_price = Column(Float, nullable=False)
    status = Column(String, nullable=False)

    __table_args__ = (
        CheckConstraint('seat_count > 0', name='check_booking_seat_count_positive'),
        CheckConstraint('total_price >= 0', name='check_total_price_positive'),
    )
