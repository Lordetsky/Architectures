import os
import grpc
from concurrent import futures
from sqlalchemy.orm import Session
from google.protobuf import empty_pb2
from google.protobuf.timestamp_pb2 import Timestamp

import flight_pb2
import flight_pb2_grpc
from database import engine, Base, SessionLocal
from models import Flight, SeatReservation
from auth_interceptor import AuthInterceptor
from redis_cache import get_from_cache, set_in_cache, invalidate_cache

Base.metadata.create_all(bind=engine)

def to_pb_timestamp(dt):
    if not dt: return None
    ts = Timestamp()
    from datetime import timezone
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    ts.FromDatetime(dt)
    return ts

class FlightServiceServicer(flight_pb2_grpc.FlightServiceServicer):
    def SearchFlights(self, request, context):
        cache_key = f"search:{request.origin}:{request.destination}:{request.date}"
        cached_data = get_from_cache(cache_key)
        if cached_data:
            flights = [flight_pb2.Flight(
                id=f["id"], airline=f["airline"], origin=f["origin"], destination=f["destination"],
                total_seats=f["total_seats"], available_seats=f["available_seats"],
                price=f["price"], status=f["status"]
            ) for f in cached_data]
            return flight_pb2.SearchFlightsResponse(flights=flights)
            
        db: Session = SessionLocal()
        try:
            query = db.query(Flight).filter(
                Flight.origin == request.origin,
                Flight.destination == request.destination,
                Flight.status == "SCHEDULED"
            )
            
            if request.date:
                from sqlalchemy import cast, Date
                from datetime import datetime
                try:
                    dt = datetime.strptime(request.date, "%Y-%m-%d").date()
                    query = query.filter(cast(Flight.departure_time, Date) == dt)
                except ValueError:
                    pass
                    
            flights_db = query.all()
            
            flight_msgs = []
            cache_list = []
            for f in flights_db:
                f_dict = {
                    "id": f.id, "airline": f.airline, "origin": f.origin, 
                    "destination": f.destination, "total_seats": f.total_seats, 
                    "available_seats": f.available_seats, "price": f.price, 
                    "status": flight_pb2.FlightStatus.Value(f.status)
                }
                msg = flight_pb2.Flight(**f_dict)
                if f.departure_time: msg.departure_time.CopyFrom(to_pb_timestamp(f.departure_time))
                if f.arrival_time: msg.arrival_time.CopyFrom(to_pb_timestamp(f.arrival_time))
                flight_msgs.append(msg)
                cache_list.append(f_dict)
            
            set_in_cache(cache_key, cache_list, ttl=300)
            return flight_pb2.SearchFlightsResponse(flights=flight_msgs)
        finally:
            db.close()

    def GetFlight(self, request, context):
        flight_id = request.flight_id
        cache_key = f"flight:{flight_id}"
        cached_data = get_from_cache(cache_key)
        if cached_data:
            return flight_pb2.FlightResponse(flight=flight_pb2.Flight(**cached_data))
            
        db: Session = SessionLocal()
        try:
            f = db.query(Flight).filter(Flight.id == flight_id).first()
            if not f:
                context.abort(grpc.StatusCode.NOT_FOUND, "Flight not found")
            
            f_dict = {
                "id": f.id, "airline": f.airline, "origin": f.origin, 
                "destination": f.destination, "total_seats": f.total_seats, 
                "available_seats": f.available_seats, "price": f.price, 
                "status": flight_pb2.FlightStatus.Value(f.status)
            }
            msg = flight_pb2.Flight(**f_dict)
            if f.departure_time: msg.departure_time.CopyFrom(to_pb_timestamp(f.departure_time))
            if f.arrival_time: msg.arrival_time.CopyFrom(to_pb_timestamp(f.arrival_time))
            set_in_cache(cache_key, f_dict, ttl=600)
            return flight_pb2.FlightResponse(flight=msg)
        finally:
            db.close()

    def ReserveSeats(self, request, context):
        db: Session = SessionLocal()
        try:
            existing_res = db.query(SeatReservation).filter(SeatReservation.booking_id == request.booking_id).first()
            if existing_res:
                return flight_pb2.ReserveSeatsResponse(reservation_id=existing_res.id)
            
            flight = db.query(Flight).with_for_update().filter(Flight.id == request.flight_id).first()
            if not flight:
                context.abort(grpc.StatusCode.NOT_FOUND, "Flight not found")
            
            if flight.available_seats < request.seat_count:
                context.abort(grpc.StatusCode.RESOURCE_EXHAUSTED, "Not enough seats")
                
            flight.available_seats -= request.seat_count
            
            reservation = SeatReservation(
                booking_id=request.booking_id,
                flight_id=request.flight_id,
                seat_count=request.seat_count,
                status="ACTIVE"
            )
            db.add(reservation)
            db.commit()
            db.refresh(reservation)
            invalidate_cache([f"flight:{flight.id}"])
            return flight_pb2.ReserveSeatsResponse(reservation_id=reservation.id)
        except Exception as e:
            db.rollback()
            context.abort(grpc.StatusCode.INTERNAL, str(e))
        finally:
            db.close()

    def ReleaseReservation(self, request, context):
        db: Session = SessionLocal()
        try:
            reservation = db.query(SeatReservation).with_for_update().filter(
                SeatReservation.booking_id == request.booking_id,
                SeatReservation.status == "ACTIVE"
            ).first()
            if not reservation:
                return empty_pb2.Empty()
                
            flight = db.query(Flight).with_for_update().filter(Flight.id == reservation.flight_id).first()
            if flight:
                flight.available_seats += reservation.seat_count
            
            reservation.status = "RELEASED"
            db.commit()
            if flight:
                invalidate_cache([f"flight:{flight.id}"])
            return empty_pb2.Empty()
        except Exception as e:
            db.rollback()
            context.abort(grpc.StatusCode.INTERNAL, str(e))
        finally:
            db.close()

def serve():
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10),
        interceptors=(AuthInterceptor(),)
    )
    flight_pb2_grpc.add_FlightServiceServicer_to_server(FlightServiceServicer(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
