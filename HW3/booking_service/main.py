from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
import grpc

from database import engine, Base, get_db
from models import Booking
import schemas
from grpc_client import call_flight_service
import flight_pb2

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Booking Service")

@app.get("/flights")
def search_flights(origin: str, destination: str, date: Optional[str] = None):
    try:
        req = flight_pb2.SearchFlightsRequest(origin=origin, destination=destination, date=date or "")
        resp = call_flight_service("SearchFlights", req)
        flights = []
        for f in resp.flights:
            flights.append({
                "id": f.id, "airline": f.airline, "origin": f.origin, "destination": f.destination,
                "total_seats": f.total_seats, "available_seats": f.available_seats,
                "price": f.price, "status": flight_pb2.FlightStatus.Name(f.status)
            })
        return flights
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/flights/{flight_id}")
def get_flight(flight_id: int):
    try:
        req = flight_pb2.GetFlightRequest(flight_id=flight_id)
        resp = call_flight_service("GetFlight", req)
        f = resp.flight
        return {
            "id": f.id, "airline": f.airline, "origin": f.origin, "destination": f.destination,
            "total_seats": f.total_seats, "available_seats": f.available_seats,
            "price": f.price, "status": flight_pb2.FlightStatus.Name(f.status)
        }
    except grpc.RpcError as e:
        if e.code() == grpc.StatusCode.NOT_FOUND:
            raise HTTPException(status_code=404, detail="Flight not found")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/bookings", response_model=schemas.BookingResponse)
def create_booking(booking_in: schemas.BookingCreate, db: Session = Depends(get_db)):
    try:
        req_flight = flight_pb2.GetFlightRequest(flight_id=booking_in.flight_id)
        flight_resp = call_flight_service("GetFlight", req_flight)
        flight = flight_resp.flight
        
        new_booking = Booking(
            user_id=booking_in.user_id,
            flight_id=booking_in.flight_id,
            passenger_name=booking_in.passenger_name,
            passenger_email=booking_in.passenger_email,
            seat_count=booking_in.seat_count,
            total_price=0.0,
            status="PENDING"
        )
        db.add(new_booking)
        db.commit()
        db.refresh(new_booking)
        
        req_reserve = flight_pb2.ReserveSeatsRequest(
            flight_id=booking_in.flight_id, 
            seat_count=booking_in.seat_count,
            booking_id=new_booking.id
        )
        call_flight_service("ReserveSeats", req_reserve)
        
        new_booking.total_price = booking_in.seat_count * flight.price
        new_booking.status = "CONFIRMED"
        db.commit()
        db.refresh(new_booking)
        return new_booking
        
    except grpc.RpcError as e:
        db.rollback()
        if 'new_booking' in locals() and new_booking.id:
            new_booking.status = "FAILED"
            db.commit()
        if e.code() == grpc.StatusCode.NOT_FOUND:
            raise HTTPException(status_code=404, detail="Flight not found")
        if e.code() == grpc.StatusCode.RESOURCE_EXHAUSTED:
            raise HTTPException(status_code=400, detail="Not enough seats")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/bookings/{booking_id}", response_model=schemas.BookingResponse)
def get_booking(booking_id: int, db: Session = Depends(get_db)):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking

@app.get("/bookings", response_model=List[schemas.BookingResponse])
def list_bookings(user_id: int, db: Session = Depends(get_db)):
    return db.query(Booking).filter(Booking.user_id == user_id).all()

@app.post("/bookings/{booking_id}/cancel")
def cancel_booking(booking_id: int, db: Session = Depends(get_db)):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.status != "CONFIRMED":
        raise HTTPException(status_code=400, detail="Only CONFIRMED bookings can be cancelled")
        
    try:
        req_release = flight_pb2.ReleaseReservationRequest(booking_id=booking.id)
        call_flight_service("ReleaseReservation", req_release)
        
        booking.status = "CANCELLED"
        db.commit()
        return {"message": "Booking cancelled"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
