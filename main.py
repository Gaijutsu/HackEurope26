"""FastAPI Backend - Hackathon Edition with CrewAI Agents"""
import os
import json

# Load .env before anything else
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt

from icalendar import Calendar, Event as ICalEvent

from database import init_db, get_db, User, Trip, ItineraryItem, Flight, Accommodation, City
from agents import planning_agent

# Initialize database
init_db()

# FastAPI app
app = FastAPI(
    title="Agentic Trip Planner API",
    description="Hackathon version - Multi-agent trip planning with CrewAI",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For hackathon - allow all
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("SECRET_KEY", "hackathon-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# Pydantic models
class UserCreate(BaseModel):
    email: str
    name: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class TripCreate(BaseModel):
    title: str
    destination: str
    start_date: str  # YYYY-MM-DD
    end_date: str  # YYYY-MM-DD
    num_travelers: int = 1
    interests: List[str] = []
    dietary_restrictions: List[str] = []
    budget_level: str = "mid"  # budget, mid, luxury

class TripResponse(BaseModel):
    id: str
    title: str
    destination: str
    start_date: str
    end_date: str
    planning_status: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class PlanResponse(BaseModel):
    cities: List[str]
    flights: List[Dict]
    accommodations: List[Dict]
    itinerary: List[Dict]
    is_country_level: bool
    planning_summary: str

# Helper functions
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Auth endpoints
@app.post("/auth/register")
def register(user: UserCreate):
    db = get_db()
    
    # Check if user exists
    existing = db.query(User).filter(User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    db_user = User(
        email=user.email,
        name=user.name,
        password_hash=hash_password(user.password),
        preferences={}
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Create token
    access_token = create_access_token(
        data={"sub": db_user.id},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": db_user.id,
            "email": db_user.email,
            "name": db_user.name
        }
    }

@app.post("/auth/login")
def login(user: UserLogin):
    db = get_db()
    
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(
        data={"sub": db_user.id},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": db_user.id,
            "email": db_user.email,
            "name": db_user.name
        }
    }

# Trip endpoints
@app.get("/trips")
def get_trips(user_id: str):
    db = get_db()
    trips = db.query(Trip).filter(Trip.user_id == user_id).all()
    return [
        {
            "id": t.id,
            "title": t.title,
            "destination": t.destination,
            "start_date": t.start_date,
            "end_date": t.end_date,
            "planning_status": t.planning_status,
            "created_at": t.created_at.isoformat()
        }
        for t in trips
    ]

@app.post("/trips")
def create_trip(trip: TripCreate, user_id: str):
    db = get_db()
    
    db_trip = Trip(
        user_id=user_id,
        title=trip.title,
        destination=trip.destination,
        destination_type="country" if planning_agent._is_likely_country(trip.destination) else "city",
        start_date=trip.start_date,
        end_date=trip.end_date,
        num_travelers=trip.num_travelers,
        interests=trip.interests,
        dietary_restrictions=trip.dietary_restrictions,
        budget_level=trip.budget_level,
        planning_status="pending",
        plan_data={}
    )
    db.add(db_trip)
    db.commit()
    db.refresh(db_trip)
    
    return {
        "id": db_trip.id,
        "title": db_trip.title,
        "destination": db_trip.destination,
        "planning_status": db_trip.planning_status,
        "message": "Trip created successfully. Start planning to generate itinerary."
    }

@app.get("/trips/{trip_id}")
def get_trip(trip_id: str, user_id: str):
    db = get_db()
    trip = db.query(Trip).filter(Trip.id == trip_id, Trip.user_id == user_id).first()
    
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    return {
        "id": trip.id,
        "title": trip.title,
        "destination": trip.destination,
        "destination_type": trip.destination_type,
        "start_date": trip.start_date,
        "end_date": trip.end_date,
        "num_travelers": trip.num_travelers,
        "interests": trip.interests,
        "dietary_restrictions": trip.dietary_restrictions,
        "budget_level": trip.budget_level,
        "planning_status": trip.planning_status,
        "plan_data": trip.plan_data,
        "created_at": trip.created_at.isoformat()
    }

@app.delete("/trips/{trip_id}")
def delete_trip(trip_id: str, user_id: str):
    db = get_db()
    trip = db.query(Trip).filter(Trip.id == trip_id, Trip.user_id == user_id).first()
    
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    db.delete(trip)
    db.commit()
    
    return {"message": "Trip deleted successfully"}

# ---------------------------------------------------------------------------
# Planning endpoints  (CrewAI powered)
# ---------------------------------------------------------------------------

def _save_plan_to_db(db, trip, plan_data: dict):
    """Persist the generated plan (flights, accommodations, itinerary) into DB rows."""
    trip.plan_data = plan_data
    trip.planning_status = "completed"
    db.commit()

    for flight in plan_data.get("flights", []):
        db.add(Flight(
            trip_id=trip.id,
            flight_type=flight["flight_type"],
            airline=flight["airline"],
            flight_number=flight["flight_number"],
            from_airport=flight["from_airport"],
            to_airport=flight["to_airport"],
            departure_datetime=flight["departure_datetime"],
            arrival_datetime=flight["arrival_datetime"],
            duration_minutes=flight["duration_minutes"],
            price=flight["price"],
            currency=flight.get("currency", "USD"),
            booking_url=flight["booking_url"],
            status="suggested",
        ))

    for acc in plan_data.get("accommodations", []):
        db.add(Accommodation(
            trip_id=trip.id,
            name=acc["name"],
            type=acc["type"],
            address=acc["address"],
            city=acc["city"],
            check_in_date=acc["check_in_date"],
            check_out_date=acc["check_out_date"],
            price_per_night=acc["price_per_night"],
            total_price=acc["total_price"],
            currency=acc.get("currency", "USD"),
            rating=acc.get("rating"),
            amenities=acc.get("amenities", []),
            booking_url=acc["booking_url"],
            status="suggested",
        ))

    for day in plan_data.get("itinerary", []):
        for item in day.get("items", []):
            db.add(ItineraryItem(
                trip_id=trip.id,
                day_number=day["day_number"],
                title=item["title"],
                description=item.get("description", ""),
                start_time=item["start_time"],
                duration_minutes=item["duration_minutes"],
                item_type=item["item_type"],
                location=item.get("location", ""),
                cost=item.get("cost_usd", item.get("cost", 0)),
                currency=item.get("currency", "USD"),
                booking_url=item.get("google_maps_url", item.get("booking_url")),
                status="planned",
                delayed_to_day=None,
                is_ai_suggested=item.get("is_ai_suggested", 1),
            ))

    db.commit()


@app.post("/trips/{trip_id}/plan")
def start_planning(trip_id: str, user_id: str):
    """Run the CrewAI planning pipeline synchronously."""
    db = get_db()
    trip = db.query(Trip).filter(Trip.id == trip_id, Trip.user_id == user_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    trip.planning_status = "in_progress"
    db.commit()

    try:
        plan_data = planning_agent.plan_trip({
            "destination": trip.destination,
            "start_date": trip.start_date,
            "end_date": trip.end_date,
            "num_travelers": trip.num_travelers,
            "interests": trip.interests,
            "dietary_restrictions": trip.dietary_restrictions,
            "budget_level": trip.budget_level,
        })

        _save_plan_to_db(db, trip, plan_data)

        return {
            "status": "completed",
            "message": "Planning completed successfully!",
            "summary": plan_data["planning_summary"],
            "cities": plan_data["cities"],
            "flights_count": len(plan_data.get("flights", [])),
            "accommodations_count": len(plan_data.get("accommodations", [])),
            "days_planned": len(plan_data.get("itinerary", [])),
        }
    except Exception as e:
        trip.planning_status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Planning failed: {str(e)}")


@app.get("/trips/{trip_id}/plan/stream")
def stream_planning(trip_id: str, user_id: str):
    """SSE endpoint - streams agent progress events as the plan is built."""
    db = get_db()
    trip = db.query(Trip).filter(Trip.id == trip_id, Trip.user_id == user_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    trip.planning_status = "in_progress"
    db.commit()

    trip_data = {
        "destination": trip.destination,
        "start_date": trip.start_date,
        "end_date": trip.end_date,
        "num_travelers": trip.num_travelers,
        "interests": trip.interests,
        "dietary_restrictions": trip.dietary_restrictions,
        "budget_level": trip.budget_level,
    }

    def event_generator():
        plan_data = None
        try:
            for event in planning_agent.plan_trip_stream(trip_data):
                if event.get("type") == "complete":
                    plan_data = event.get("plan", {})
                    yield f"data: {json.dumps(event, default=str)}\n\n"
                else:
                    yield f"data: {json.dumps(event, default=str)}\n\n"

            # Save to DB after stream completes
            if plan_data:
                db2 = get_db()
                trip2 = db2.query(Trip).filter(Trip.id == trip_id).first()
                if trip2:
                    _save_plan_to_db(db2, trip2, plan_data)
        except Exception as exc:
            db3 = get_db()
            trip3 = db3.query(Trip).filter(Trip.id == trip_id).first()
            if trip3:
                trip3.planning_status = "failed"
                db3.commit()
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

@app.get("/trips/{trip_id}/plan/status")
def get_planning_status(trip_id: str, user_id: str):
    db = get_db()
    trip = db.query(Trip).filter(Trip.id == trip_id, Trip.user_id == user_id).first()
    
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    return {
        "trip_id": trip.id,
        "planning_status": trip.planning_status,
        "has_plan": bool(trip.plan_data)
    }

# Itinerary endpoints
@app.get("/trips/{trip_id}/itinerary")
def get_itinerary(trip_id: str, user_id: str):
    db = get_db()
    trip = db.query(Trip).filter(Trip.id == trip_id, Trip.user_id == user_id).first()
    
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    items = db.query(ItineraryItem).filter(ItineraryItem.trip_id == trip_id).all()
    
    # Group by day
    days = {}
    for item in items:
        if item.day_number not in days:
            days[item.day_number] = []
        days[item.day_number].append({
            "id": item.id,
            "day_number": item.day_number,
            "title": item.title,
            "description": item.description,
            "start_time": item.start_time,
            "duration_minutes": item.duration_minutes,
            "item_type": item.item_type,
            "location": item.location,
            "cost": item.cost,
            "cost_usd": item.cost,
            "currency": item.currency,
            "google_maps_url": item.booking_url or "",
            "booking_url": item.booking_url,
            "status": item.status,
            "delayed_to_day": item.delayed_to_day,
            "is_ai_suggested": item.is_ai_suggested
        })
    
    # Sort items within each day by start_time
    for day_num in days:
        days[day_num].sort(key=lambda x: x["start_time"])
    
    return {
        "trip_id": trip_id,
        "destination": trip.destination,
        "days": [
            {
                "day_number": day_num,
                "items": days[day_num]
            }
            for day_num in sorted(days.keys())
        ]
    }

@app.put("/trips/{trip_id}/itinerary/items/{item_id}/delay")
def delay_item(trip_id: str, item_id: str, new_day: int, user_id: str):
    db = get_db()
    
    # Verify trip exists and belongs to user
    trip = db.query(Trip).filter(Trip.id == trip_id, Trip.user_id == user_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    # Get item
    item = db.query(ItineraryItem).filter(ItineraryItem.id == item_id, ItineraryItem.trip_id == trip_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Update item
    item.status = "delayed"
    item.delayed_to_day = new_day
    db.commit()
    
    return {
        "message": f"Item delayed to day {new_day}",
        "item_id": item_id,
        "new_day": new_day
    }

@app.put("/trips/{trip_id}/itinerary/items/{item_id}/complete")
def complete_item(trip_id: str, item_id: str, user_id: str):
    db = get_db()
    
    trip = db.query(Trip).filter(Trip.id == trip_id, Trip.user_id == user_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    item = db.query(ItineraryItem).filter(ItineraryItem.id == item_id, ItineraryItem.trip_id == trip_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    item.status = "completed"
    db.commit()
    
    return {"message": "Item marked as completed"}


@app.get("/trips/{trip_id}/ical")
def get_trip_ical(trip_id: str, user_id: str):
    """Download an iCal (.ics) file for the trip itinerary."""
    db = get_db()
    trip = db.query(Trip).filter(Trip.id == trip_id, Trip.user_id == user_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    items = db.query(ItineraryItem).filter(
        ItineraryItem.trip_id == trip_id
    ).order_by(ItineraryItem.day_number, ItineraryItem.start_time).all()

    cal = Calendar()
    cal.add("prodid", "-//Agentic Trip Planner//EN")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("x-wr-calname", trip.title)

    trip_start = datetime.strptime(trip.start_date, "%Y-%m-%d")

    for item in items:
        ev = ICalEvent()
        ev.add("summary", item.title)
        ev.add("description", item.description or "")

        event_date = trip_start + timedelta(days=item.day_number - 1)
        try:
            parts = item.start_time.split(":")
            hour, minute = int(parts[0]), int(parts[1])
            ev_start = event_date.replace(hour=hour, minute=minute)
        except (ValueError, IndexError, AttributeError):
            ev_start = event_date.replace(hour=9, minute=0)

        ev.add("dtstart", ev_start)
        ev.add("dtend", ev_start + timedelta(minutes=item.duration_minutes or 60))

        if item.location:
            ev.add("location", item.location)

        ev.add("uid", f"{item.id}@agentic-trip-planner")
        cal.add_component(ev)

    ics_bytes = cal.to_ical()
    safe_title = trip.title.replace(" ", "_")
    return Response(
        content=ics_bytes,
        media_type="text/calendar",
        headers={"Content-Disposition": f'attachment; filename="{safe_title}.ics"'},
    )


# Flight endpoints
@app.get("/trips/{trip_id}/flights")
def get_flights(trip_id: str, user_id: str):
    db = get_db()
    
    trip = db.query(Trip).filter(Trip.id == trip_id, Trip.user_id == user_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    flights = db.query(Flight).filter(Flight.trip_id == trip_id).all()
    
    return [
        {
            "id": f.id,
            "flight_type": f.flight_type,
            "airline": f.airline,
            "flight_number": f.flight_number,
            "from_airport": f.from_airport,
            "to_airport": f.to_airport,
            "departure_datetime": f.departure_datetime,
            "arrival_datetime": f.arrival_datetime,
            "duration_minutes": f.duration_minutes,
            "price": f.price,
            "currency": f.currency,
            "booking_url": f.booking_url,
            "status": f.status
        }
        for f in flights
    ]

@app.post("/trips/{trip_id}/flights/{flight_id}/book")
def book_flight(trip_id: str, flight_id: str, user_id: str):
    db = get_db()
    
    trip = db.query(Trip).filter(Trip.id == trip_id, Trip.user_id == user_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    flight = db.query(Flight).filter(Flight.id == flight_id, Flight.trip_id == trip_id).first()
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")
    
    flight.status = "booked"
    db.commit()
    
    return {"message": "Flight marked as booked", "booking_url": flight.booking_url}

# Accommodation endpoints
@app.get("/trips/{trip_id}/accommodations")
def get_accommodations(trip_id: str, user_id: str):
    db = get_db()
    
    trip = db.query(Trip).filter(Trip.id == trip_id, Trip.user_id == user_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    accs = db.query(Accommodation).filter(Accommodation.trip_id == trip_id).all()
    
    return [
        {
            "id": a.id,
            "name": a.name,
            "type": a.type,
            "address": a.address,
            "city": a.city,
            "check_in_date": a.check_in_date,
            "check_out_date": a.check_out_date,
            "price_per_night": a.price_per_night,
            "total_price": a.total_price,
            "currency": a.currency,
            "rating": a.rating,
            "amenities": a.amenities,
            "booking_url": a.booking_url,
            "status": a.status
        }
        for a in accs
    ]

@app.post("/trips/{trip_id}/accommodations/{acc_id}/book")
def book_accommodation(trip_id: str, acc_id: str, user_id: str):
    db = get_db()
    
    trip = db.query(Trip).filter(Trip.id == trip_id, Trip.user_id == user_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    acc = db.query(Accommodation).filter(Accommodation.id == acc_id, Accommodation.trip_id == trip_id).first()
    if not acc:
        raise HTTPException(status_code=404, detail="Accommodation not found")
    
    acc.status = "booked"
    db.commit()
    
    return {"message": "Accommodation marked as booked", "booking_url": acc.booking_url}

# Search endpoints
@app.get("/search/cities")
def search_cities(q: str):
    db = get_db()
    cities = db.query(City).filter(City.name.ilike(f"%{q}%")).limit(10).all()
    
    return [
        {
            "id": c.id,
            "name": c.name,
            "country": c.country,
            "iata_code": c.iata_code
        }
        for c in cities
    ]

# Health check
@app.get("/health")
def health_check():
    from agents import _llm_name
    return {
        "status": "ok",
        "version": "2.0.0",
        "engine": "CrewAI",
        "llm": _llm_name(),
        "llm_provider": os.getenv("LLM_PROVIDER", "openai"),
        "agents": [
            "DestinationResearcher",
            "CitySelector",
            "FlightFinder",
            "AccommodationFinder",
            "ItineraryPlanner",
        ],
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
