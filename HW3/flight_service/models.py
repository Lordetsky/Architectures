from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, CheckConstraint
from database import Base

class Flight(Base):
    __tablename__ = "flights"
    id = Column(Integer, primary_key=True, index=True)
    airline = Column(String, nullable=False)
    origin = Column(String, nullable=False)
    destination = Column(String, nullable=False)
    departure_time = Column(DateTime(timezone=True), nullable=False)
    arrival_time = Column(DateTime(timezone=True), nullable=False)
    total_seats = Column(Integer, nullable=False)
    available_seats = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    status = Column(String, nullable=False)

    __table_args__ = (
        CheckConstraint('available_seats >= 0', name='check_available_seats_positive'),
        CheckConstraint('total_seats > 0', name='check_total_seats_positive'),
        CheckConstraint('price > 0', name='check_price_positive'),
    )

class SeatReservation(Base):
    __tablename__ = "seat_reservations"
    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, unique=True, nullable=False)
    flight_id = Column(Integer, ForeignKey("flights.id"), nullable=False)
    seat_count = Column(Integer, nullable=False)
    status = Column(String, nullable=False)

    __table_args__ = (
        CheckConstraint('seat_count > 0', name='check_seat_count_positive'),
    )
