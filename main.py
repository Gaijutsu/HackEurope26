"""FastAPI Backend - Hackathon Edition with CrewAI Agents"""
import os
import json
import uuid
import shutil

# Load .env before anything else
from dotenv import load_dotenv
load_dotenv()

import stripe

from fastapi import FastAPI, HTTPException, Depends, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt

from icalendar import Calendar, Event as ICalEvent

from database import init_db, get_db, User, Trip, ItineraryItem, Flight, Accommodation, City, ChatMessage
from agents import planning_agent

# Initialize database
init_db()

# FastAPI app
app = FastAPI(
    title="Agentic Trip Planner API",
    description="Hackathon version - Multi-agent trip planning with CrewAI",
    version="2.0.0"
)

# Pinterest image storage — reuse frontend/public so mock data is available
PINTEREST_DIR = os.path.join(os.path.dirname(__file__), "frontend", "public", "pinterest")
os.makedirs(PINTEREST_DIR, exist_ok=True)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For hackathon - allow all
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Stripe configuration
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

CREDIT_PACKAGES = {
    "1": {"credits": 1, "price_cents": 199, "label": "1 Trip Credit"},
    "5": {"credits": 5, "price_cents": 799, "label": "5 Trip Credits"},
    "10": {"credits": 10, "price_cents": 1199, "label": "10 Trip Credits"},
}

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
    origin_city: str = ""
    start_date: str  # YYYY-MM-DD
    end_date: str  # YYYY-MM-DD
    num_travelers: int = 1
    interests: List[str] = []
    dietary_restrictions: List[str] = []
    budget_level: int = 1000  # total trip budget in USD

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

class ChatRequest(BaseModel):
    message: str

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
            "name": db_user.name,
            "credits": db_user.credits
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
            "name": db_user.name,
            "credits": db_user.credits
        }
    }

# ── Credits endpoints ──────────────────────────────────────────────────────

@app.get("/credits")
def get_credits(user_id: str):
    """Return the current credit balance for a user."""
    db = get_db()
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"credits": user.credits}


class AdjustCreditsRequest(BaseModel):
    amount: int  # positive to add, negative to remove


@app.post("/credits/adjust")
def adjust_credits(body: AdjustCreditsRequest, user_id: str):
    """Secret endpoint to add/remove credits (used by hidden destination codes)."""
    db = get_db()
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.credits = max(0, user.credits + body.amount)
    db.commit()
    db.refresh(user)
    return {"credits": user.credits}


class CheckoutRequest(BaseModel):
    package: str  # '1', '5', or '10'


@app.post("/credits/checkout")
def create_checkout_session(body: CheckoutRequest, user_id: str):
    """Create a Stripe Checkout session for purchasing trip credits."""
    pkg = CREDIT_PACKAGES.get(body.package)
    if not pkg:
        raise HTTPException(status_code=400, detail="Invalid package")

    # Always verify the user exists first
    db = get_db()
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not stripe.api_key:
        # If Stripe is not configured, grant credits directly (hackathon fallback)
        user.credits += pkg["credits"]
        db.commit()
        db.refresh(user)
        return {"fallback": True, "credits": user.credits}

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "unit_amount": pkg["price_cents"],
                    "product_data": {"name": pkg["label"]},
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=f"{FRONTEND_URL}/credits/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{FRONTEND_URL}/credits",
            metadata={"user_id": user_id, "credits": str(pkg["credits"])},
        )
        return {"url": session.url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")


from fastapi import Request as FastAPIRequest


@app.post("/credits/webhook")
async def stripe_webhook(request: FastAPIRequest):
    """Handle Stripe webhook for completed checkout sessions."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    if STRIPE_WEBHOOK_SECRET:
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
        except (ValueError, stripe.error.SignatureVerificationError):
            raise HTTPException(status_code=400, detail="Invalid webhook signature")
    else:
        event = json.loads(payload)

    if event.get("type") == "checkout.session.completed":
        session = event["data"]["object"]
        metadata = session.get("metadata", {})
        item_type = metadata.get("item_type", "")
        item_id = metadata.get("item_id", "")

        if item_type == "flight" and item_id:
            # Flight booking payment completed
            db = get_db()
            flight = db.query(Flight).filter(Flight.id == item_id).first()
            if flight:
                flight.status = "booked"
                db.commit()
        elif item_type == "accommodation" and item_id:
            # Accommodation booking payment completed
            db = get_db()
            acc = db.query(Accommodation).filter(Accommodation.id == item_id).first()
            if acc:
                acc.status = "booked"
                db.commit()
        else:
            # Legacy: credit purchase
            user_id = metadata.get("user_id")
            credits_str = metadata.get("credits", "0")
            if user_id and int(credits_str) > 0:
                db = get_db()
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    user.credits += int(credits_str)
                    db.commit()

    return {"status": "ok"}


@app.get("/credits/success")
def credits_success(session_id: str = "", user_id: str = ""):
    """Verify a completed checkout session and grant credits if not already granted.

    This replaces the need for webhooks — when the user is redirected back from
    Stripe Checkout, we retrieve the session from Stripe's API, check the
    metadata, and grant credits if the payment succeeded.
    """
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id required")
    db = get_db()
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # If we have a session_id and Stripe is configured, verify & grant credits
    if session_id and stripe.api_key:
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            if session.payment_status == "paid":
                # Use the session ID as an idempotency key to avoid double-granting
                idempotency_key = f"stripe_session_{session.id}"
                from database import get_cache, set_cache
                if not get_cache(idempotency_key):
                    credits_to_add = int(session.metadata.get("credits", "0"))
                    if credits_to_add > 0:
                        user.credits += credits_to_add
                        db.commit()
                        db.refresh(user)
                    set_cache(idempotency_key, True, ttl_seconds=86400)
        except Exception:
            pass  # Fall through — return current balance regardless

    return {"credits": user.credits}


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
        origin_city=trip.origin_city,
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
                travel_info=item.get("travel_info", {}),
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

    # Don't restart planning that is already done or running
    if trip.planning_status == "completed" and trip.plan_data:
        return {
            "status": "completed",
            "message": "Planning already completed.",
            "summary": trip.plan_data.get("planning_summary", ""),
            "cities": trip.plan_data.get("cities", []),
            "flights_count": len(trip.plan_data.get("flights", [])),
            "accommodations_count": len(trip.plan_data.get("accommodations", [])),
            "days_planned": len(trip.plan_data.get("itinerary", [])),
        }
    if trip.planning_status == "in_progress":
        raise HTTPException(status_code=409, detail="Planning is already in progress")

    trip.planning_status = "in_progress"
    db.commit()

    try:
        plan_data = planning_agent.plan_trip({
            "destination": trip.destination,
            "origin_city": trip.origin_city or "",
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

    # If already completed, return the cached plan as a single SSE event
    if trip.planning_status == "completed" and trip.plan_data:
        pass  # no credit charge for cached plans
    elif trip.planning_status != "in_progress":
        # Deduct 1 credit for a new planning run
        planner_user = db.query(User).filter(User.id == user_id).first()
        if not planner_user or planner_user.credits < 1:
            raise HTTPException(status_code=402, detail="Not enough trip credits. Purchase more to plan a trip.")
        planner_user.credits -= 1
        db.commit()

    if trip.planning_status == "completed" and trip.plan_data:
        def _cached():
            event = {"type": "complete", "agent": "Orchestrator",
                     "status": "complete", "message": "Trip plan already exists.",
                     "plan": trip.plan_data}
            yield f"data: {json.dumps(event, default=str)}\n\n"
        return StreamingResponse(
            _cached(), media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # Reject if another stream is already running for this trip
    if trip.planning_status == "in_progress":
        raise HTTPException(status_code=409, detail="Planning is already in progress")

    trip.planning_status = "in_progress"
    db.commit()

    trip_data = {
        "destination": trip.destination,
        "origin_city": trip.origin_city or "",
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


@app.post("/trips/{trip_id}/regenerate-itinerary")
def regenerate_itinerary(trip_id: str, user_id: str):
    """Re-generate the itinerary using cached destination data and user-selected flights/accommodations.

    This avoids re-running the full 7-agent crew.  Only the ItineraryPlanner runs,
    using the cached plan_data for research / cities / local gems and the user's
    currently selected (or all if none selected) flights and accommodations.
    """
    db = get_db()
    trip = db.query(Trip).filter(Trip.id == trip_id, Trip.user_id == user_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    if not trip.plan_data:
        raise HTTPException(status_code=400, detail="Trip has no existing plan to regenerate from")

    # Gather selected flights (fall back to all if none selected)
    all_flights = db.query(Flight).filter(Flight.trip_id == trip_id).all()
    selected_flights = [f for f in all_flights if f.status == "selected"]
    if not selected_flights:
        selected_flights = all_flights
    flight_dicts = [
        {
            "flight_type": f.flight_type,
            "airline": f.airline,
            "from_airport": f.from_airport,
            "to_airport": f.to_airport,
            "departure_datetime": f.departure_datetime,
            "arrival_datetime": f.arrival_datetime,
            "price": f.price,
        }
        for f in selected_flights
    ]

    # Gather selected accommodations (fall back to all if none selected)
    all_accs = db.query(Accommodation).filter(Accommodation.trip_id == trip_id).all()
    selected_accs = [a for a in all_accs if a.status == "selected"]
    if not selected_accs:
        selected_accs = all_accs
    accom_dicts = [
        {
            "name": a.name,
            "city": a.city,
            "address": a.address,
            "price_per_night": a.price_per_night,
        }
        for a in selected_accs
    ]

    trip_data = {
        "destination": trip.destination,
        "origin_city": trip.origin_city or "",
        "start_date": trip.start_date,
        "end_date": trip.end_date,
        "num_travelers": trip.num_travelers,
        "interests": trip.interests,
        "dietary_restrictions": trip.dietary_restrictions,
        "budget_level": trip.budget_level,
    }

    try:
        result = planning_agent.regenerate_itinerary(
            trip_data, trip.plan_data, flight_dicts, accom_dicts
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Itinerary regeneration failed: {str(e)}")

    new_itinerary = result["itinerary"]

    # Delete old itinerary items
    db.query(ItineraryItem).filter(ItineraryItem.trip_id == trip_id).delete()

    # Enrich with travel routes between consecutive items
    from agents.RouteAgent import compute_routes_for_day as _compute_routes
    for day in new_itinerary:
        city = day.get("city", "")
        items = day.get("items", [])
        if len(items) > 1:
            _compute_routes(items, city)
        elif items:
            items[0].setdefault("travel_info", {})

    # Save new itinerary items
    for day in new_itinerary:
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
                travel_info=item.get("travel_info", {}),
                status="planned",
                delayed_to_day=None,
                is_ai_suggested=item.get("is_ai_suggested", 1),
            ))

    # Update plan_data with new itinerary (preserve other cached data)
    updated_plan = dict(trip.plan_data)
    updated_plan["itinerary"] = new_itinerary
    trip.plan_data = updated_plan
    db.commit()

    return {
        "status": "completed",
        "message": "Itinerary regenerated successfully!",
        "days_planned": len(new_itinerary),
    }

# ---------------------------------------------------------------------------
# Chat-based itinerary modification
# ---------------------------------------------------------------------------

@app.post("/trips/{trip_id}/chat")
def chat_modify_itinerary(trip_id: str, body: ChatRequest, user_id: str):
    """Use an LLM agent to modify the itinerary based on a natural-language message."""
    db = get_db()
    trip = db.query(Trip).filter(Trip.id == trip_id, Trip.user_id == user_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    if not trip.plan_data or not trip.plan_data.get("itinerary"):
        raise HTTPException(status_code=400, detail="Trip has no itinerary to modify")

    trip_data = {
        "destination": trip.destination,
        "origin_city": trip.origin_city or "",
        "start_date": trip.start_date,
        "end_date": trip.end_date,
        "num_travelers": trip.num_travelers,
        "interests": trip.interests,
        "dietary_restrictions": trip.dietary_restrictions,
        "budget_level": trip.budget_level,
    }

    current_itinerary = trip.plan_data["itinerary"]

    # Load conversation history for multi-turn context
    chat_history = db.query(ChatMessage).filter(
        ChatMessage.trip_id == trip_id
    ).order_by(ChatMessage.created_at).all()
    history_list = [{"role": m.role, "content": m.content} for m in chat_history]

    try:
        result = planning_agent.modify_itinerary_chat(
            trip_data, current_itinerary, body.message, history_list
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat modification failed: {str(e)}")

    new_itinerary = result["itinerary"]
    reply = result["reply"]
    travel_prefs = result.get("travel_prefs", {})

    # Delete old itinerary items and save new ones
    db.query(ItineraryItem).filter(ItineraryItem.trip_id == trip_id).delete()

    for day in new_itinerary:
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
                travel_info=item.get("travel_info", {}),
                status="planned",
                delayed_to_day=None,
                is_ai_suggested=item.get("is_ai_suggested", 1),
            ))

    # Update plan_data with new itinerary and travel preferences
    updated_plan = dict(trip.plan_data)
    updated_plan["itinerary"] = new_itinerary
    if travel_prefs and (travel_prefs.get("avoid") or travel_prefs.get("prefer")):
        updated_plan["travel_prefs"] = travel_prefs
    trip.plan_data = updated_plan

    # Persist chat messages for multi-turn context
    db.add(ChatMessage(trip_id=trip_id, role="user", content=body.message))
    db.add(ChatMessage(trip_id=trip_id, role="assistant", content=reply))
    db.commit()

    return {
        "reply": reply,
        "days_planned": len(new_itinerary),
        "travel_prefs": travel_prefs,
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
            "travel_info": item.travel_info or {},
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

    if not stripe.api_key:
        # Stripe not configured — just mark as booked (hackathon fallback)
        flight.status = "booked"
        db.commit()
        return {"message": "Flight marked as booked", "booking_url": flight.booking_url, "fallback": True}

    try:
        price_cents = int(flight.price * 100)
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": (flight.currency or "USD").lower(),
                    "unit_amount": price_cents,
                    "product_data": {
                        "name": f"Flight {flight.flight_number}: {flight.from_airport} → {flight.to_airport}",
                        "description": f"{flight.airline} — {flight.departure_datetime[:10]}",
                    },
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=f"{FRONTEND_URL}/trips/{trip_id}/flights?booked={flight_id}&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{FRONTEND_URL}/trips/{trip_id}/flights",
            metadata={
                "user_id": user_id,
                "trip_id": trip_id,
                "item_type": "flight",
                "item_id": flight_id,
            },
        )
        return {"url": session.url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")


@app.put("/trips/{trip_id}/flights/{flight_id}/select")
def select_flight(trip_id: str, flight_id: str, user_id: str):
    """Select a flight option. Resets other flights of the same type to 'suggested'."""
    db = get_db()

    trip = db.query(Trip).filter(Trip.id == trip_id, Trip.user_id == user_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    flight = db.query(Flight).filter(Flight.id == flight_id, Flight.trip_id == trip_id).first()
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")

    # Reset all flights of the same type (outbound/return) to suggested
    db.query(Flight).filter(
        Flight.trip_id == trip_id,
        Flight.flight_type == flight.flight_type,
    ).update({"status": "suggested"})

    flight.status = "selected"
    db.commit()

    return {"message": f"Flight {flight_id} selected", "flight_type": flight.flight_type}


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

    if not stripe.api_key:
        # Stripe not configured — just mark as booked (hackathon fallback)
        acc.status = "booked"
        db.commit()
        return {"message": "Accommodation marked as booked", "booking_url": acc.booking_url, "fallback": True}

    try:
        price_cents = int(acc.total_price * 100)
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": (acc.currency or "USD").lower(),
                    "unit_amount": price_cents,
                    "product_data": {
                        "name": f"{acc.name} — {acc.city}",
                        "description": f"{acc.check_in_date} → {acc.check_out_date} ({acc.type})",
                    },
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=f"{FRONTEND_URL}/trips/{trip_id}/accommodations?booked={acc_id}&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{FRONTEND_URL}/trips/{trip_id}/accommodations",
            metadata={
                "user_id": user_id,
                "trip_id": trip_id,
                "item_type": "accommodation",
                "item_id": acc_id,
            },
        )
        return {"url": session.url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")


@app.put("/trips/{trip_id}/accommodations/{acc_id}/select")
def select_accommodation(trip_id: str, acc_id: str, user_id: str):
    """Select an accommodation option. Resets other accommodations in the same city to 'suggested'."""
    db = get_db()

    trip = db.query(Trip).filter(Trip.id == trip_id, Trip.user_id == user_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    acc = db.query(Accommodation).filter(Accommodation.id == acc_id, Accommodation.trip_id == trip_id).first()
    if not acc:
        raise HTTPException(status_code=404, detail="Accommodation not found")

    # Reset all accommodations in the same city to suggested
    db.query(Accommodation).filter(
        Accommodation.trip_id == trip_id,
        Accommodation.city == acc.city,
    ).update({"status": "suggested"})

    acc.status = "selected"
    db.commit()

    return {"message": f"Accommodation {acc_id} selected", "city": acc.city}


@app.get("/trips/{trip_id}/booking/verify")
def verify_booking(trip_id: str, item_type: str, item_id: str, session_id: str = "", user_id: str = ""):
    """Verify a Stripe Checkout session for flight/hotel booking and mark as booked."""
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id required")
    db = get_db()
    trip = db.query(Trip).filter(Trip.id == trip_id, Trip.user_id == user_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    if session_id and stripe.api_key:
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            if session.payment_status == "paid":
                idempotency_key = f"booking_{session.id}"
                from database import get_cache, set_cache
                if not get_cache(idempotency_key):
                    if item_type == "flight":
                        flight = db.query(Flight).filter(Flight.id == item_id, Flight.trip_id == trip_id).first()
                        if flight:
                            flight.status = "booked"
                    elif item_type == "accommodation":
                        acc = db.query(Accommodation).filter(Accommodation.id == item_id, Accommodation.trip_id == trip_id).first()
                        if acc:
                            acc.status = "booked"
                    db.commit()
                    set_cache(idempotency_key, True, ttl_seconds=86400)
        except Exception:
            pass

    return {"status": "ok"}


# ── Budget tracker ─────────────────────────────────────────────────────────

@app.get("/trips/{trip_id}/budget")
def get_trip_budget(trip_id: str, user_id: str):
    """Calculate budget breakdown for a trip: booked, selected, and estimated costs."""
    db = get_db()
    trip = db.query(Trip).filter(Trip.id == trip_id, Trip.user_id == user_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    flights = db.query(Flight).filter(Flight.trip_id == trip_id).all()
    accommodations = db.query(Accommodation).filter(Accommodation.trip_id == trip_id).all()
    items = db.query(ItineraryItem).filter(ItineraryItem.trip_id == trip_id).all()

    # Budget level → daily estimate
    daily_budget_map = {"budget": 100, "mid": 225, "luxury": 500}
    duration = 1
    try:
        from datetime import datetime as _dt
        d = (_dt.strptime(trip.end_date, "%Y-%m-%d") - _dt.strptime(trip.start_date, "%Y-%m-%d")).days + 1
        duration = max(d, 1)
    except Exception:
        pass
    daily_rate = daily_budget_map.get(trip.budget_level, 225)
    estimated_total = daily_rate * duration * (trip.num_travelers or 1)

    flight_booked = sum(f.price or 0 for f in flights if f.status == "booked")
    flight_selected = sum(f.price or 0 for f in flights if f.status == "selected")
    accom_booked = sum(a.total_price or 0 for a in accommodations if a.status == "booked")
    accom_selected = sum(a.total_price or 0 for a in accommodations if a.status == "selected")
    activity_cost = sum(i.cost or 0 for i in items)

    total_booked = flight_booked + accom_booked
    total_planned = flight_selected + accom_selected + activity_cost

    return {
        "estimated_budget": round(estimated_total, 2),
        "total_booked": round(total_booked, 2),
        "total_planned": round(total_planned, 2),
        "total_all": round(total_booked + total_planned, 2),
        "breakdown": {
            "flights_booked": round(flight_booked, 2),
            "flights_selected": round(flight_selected, 2),
            "accommodations_booked": round(accom_booked, 2),
            "accommodations_selected": round(accom_selected, 2),
            "activities": round(activity_cost, 2),
        },
        "budget_level": trip.budget_level,
        "duration_days": duration,
        "num_travelers": trip.num_travelers or 1,
    }


# ── Disruption / weather monitor ──────────────────────────────────────────

@app.get("/trips/{trip_id}/disruptions")
def get_disruptions(trip_id: str, user_id: str):
    """Check weather forecast for the trip destination and flag potential disruptions."""
    db = get_db()
    trip = db.query(Trip).filter(Trip.id == trip_id, Trip.user_id == user_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    alerts: list[dict] = []

    # Use Open-Meteo free API for weather forecast (no key needed)
    try:
        import requests as req
        from datetime import datetime as _dt

        # Geocode the destination
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={trip.destination}&count=1"
        geo_resp = req.get(geo_url, timeout=5).json()
        results = geo_resp.get("results", [])
        if not results:
            return {"alerts": [], "message": "Could not geocode destination"}

        lat = results[0]["latitude"]
        lon = results[0]["longitude"]

        # Get weather forecast
        weather_url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}"
            f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max,weather_code"
            f"&start_date={trip.start_date}&end_date={trip.end_date}"
            f"&timezone=auto"
        )
        weather_resp = req.get(weather_url, timeout=5).json()
        daily = weather_resp.get("daily", {})
        dates = daily.get("time", [])
        precip = daily.get("precipitation_sum", [])
        wind = daily.get("wind_speed_10m_max", [])
        codes = daily.get("weather_code", [])
        temp_max = daily.get("temperature_2m_max", [])
        temp_min = daily.get("temperature_2m_min", [])

        try:
            trip_start = _dt.strptime(trip.start_date, "%Y-%m-%d")
        except Exception:
            trip_start = _dt.now()

        for i, date in enumerate(dates):
            day_num = i + 1
            rain = precip[i] if i < len(precip) else 0
            w = wind[i] if i < len(wind) else 0
            code = codes[i] if i < len(codes) else 0
            t_max = temp_max[i] if i < len(temp_max) else None
            t_min = temp_min[i] if i < len(temp_min) else None

            # Heavy rain alert
            if rain and rain > 10:
                alerts.append({
                    "type": "weather",
                    "severity": "high" if rain > 25 else "medium",
                    "day_number": day_num,
                    "date": date,
                    "title": f"🌧️ Heavy rain forecast ({rain:.0f}mm)",
                    "message": f"Day {day_num} ({date}): {rain:.0f}mm of rain expected. Consider indoor activities.",
                    "suggestion": "Swap outdoor activities for museums, galleries, or covered markets.",
                    "auto_prompt": "It's raining heavily — swap outdoor activities for indoor alternatives",
                })
            elif rain and rain > 3:
                alerts.append({
                    "type": "weather",
                    "severity": "low",
                    "day_number": day_num,
                    "date": date,
                    "title": f"🌦️ Light rain possible ({rain:.1f}mm)",
                    "message": f"Day {day_num} ({date}): Light rain possible. Bring an umbrella.",
                    "suggestion": "Pack an umbrella. Outdoor plans should be fine.",
                })

            # High wind alert
            if w and w > 50:
                alerts.append({
                    "type": "weather",
                    "severity": "medium",
                    "day_number": day_num,
                    "date": date,
                    "title": f"💨 Strong winds ({w:.0f} km/h)",
                    "message": f"Day {day_num} ({date}): Wind speeds up to {w:.0f} km/h.",
                    "suggestion": "Avoid exposed viewpoints or boat tours.",
                    "auto_prompt": f"Strong winds on day {day_num} — avoid exposed outdoor activities",
                })

            # Extreme cold
            if t_min is not None and t_min < -5:
                alerts.append({
                    "type": "weather",
                    "severity": "medium",
                    "day_number": day_num,
                    "date": date,
                    "title": f"🥶 Very cold ({t_min:.0f}°C)",
                    "message": f"Day {day_num}: Temperatures as low as {t_min:.0f}°C.",
                    "suggestion": "Dress warmly. Consider indoor activities in the morning.",
                })

            # Extreme heat
            if t_max is not None and t_max > 38:
                alerts.append({
                    "type": "weather",
                    "severity": "medium",
                    "day_number": day_num,
                    "date": date,
                    "title": f"🔥 Extreme heat ({t_max:.0f}°C)",
                    "message": f"Day {day_num}: Temperatures up to {t_max:.0f}°C.",
                    "suggestion": "Schedule outdoor activities for early morning or evening. Stay hydrated.",
                    "auto_prompt": f"It's extremely hot on day {day_num} — move outdoor activities to early morning or evening",
                })

    except Exception as e:
        return {"alerts": [], "message": f"Weather check failed: {str(e)}"}

    return {
        "alerts": alerts,
        "destination": trip.destination,
        "checked_at": datetime.utcnow().isoformat(),
    }


# ── Travel guide generator (Claude 200K context) ──────────────────────────

class TravelGuideRequest(BaseModel):
    sections: List[str] = []  # optional: override which sections to generate


@app.post("/trips/{trip_id}/travel-guide")
def generate_travel_guide(trip_id: str, user_id: str, body: TravelGuideRequest = None):
    """Generate a comprehensive travel guide using the full trip plan context.
    
    Leverages Claude's 200K context window to produce a rich guide including
    cultural tips, phrasebook, packing list, emergency contacts, and more.
    """
    db = get_db()
    trip = db.query(Trip).filter(Trip.id == trip_id, Trip.user_id == user_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    if not trip.plan_data:
        raise HTTPException(status_code=400, detail="Trip has no plan data yet")

    plan_json = json.dumps(trip.plan_data, indent=2, default=str)

    flights = db.query(Flight).filter(Flight.trip_id == trip_id).all()
    flight_info = json.dumps([
        {"airline": f.airline, "flight_number": f.flight_number,
         "from": f.from_airport, "to": f.to_airport,
         "departure": f.departure_datetime, "status": f.status}
        for f in flights
    ], indent=2)

    accommodations = db.query(Accommodation).filter(Accommodation.trip_id == trip_id).all()
    accom_info = json.dumps([
        {"name": a.name, "city": a.city, "address": a.address,
         "check_in": a.check_in_date, "check_out": a.check_out_date, "status": a.status}
        for a in accommodations
    ], indent=2)

    prompt = f"""You are an expert travel guide writer. Generate a comprehensive, beautifully
formatted travel guide for this trip. Use the COMPLETE trip plan data below.

TRIP DETAILS:
- Destination: {trip.destination}
- Dates: {trip.start_date} to {trip.end_date}
- Travelers: {trip.num_travelers}
- Budget: {trip.budget_level}
- Interests: {json.dumps(trip.interests)}
- Dietary restrictions: {json.dumps(trip.dietary_restrictions)}

COMPLETE ITINERARY & PLAN DATA:
{plan_json}

FLIGHTS:
{flight_info}

ACCOMMODATIONS:
{accom_info}

Generate the following sections in MARKDOWN format:

## 🌍 Destination Overview
Brief overview of the destination(s), best time to visit, overall vibe.

## 🗣️ Essential Phrasebook
20+ useful phrases in the local language(s) with pronunciation guides. Include greetings,
ordering food, asking directions, emergencies, and polite expressions.

## 🎒 Packing List
Customized packing list based on the destination, weather, activities planned, and trip duration.
Group by category (clothing, electronics, documents, toiletries, etc.)

## 🍽️ Food & Dining Guide
Must-try local dishes, restaurant etiquette, tipping culture, dietary restriction tips,
food safety advice, and recommended restaurants from the itinerary.

## 🚇 Transportation Guide
How to get from the airport, public transit overview, ride-hailing apps available,
city-specific transport tips, and passes/cards to buy.

## 💰 Money & Budget Tips
Local currency, exchange rates, tipping culture, average costs for meals/transport/attractions,
money-saving tips specific to the destination.

## 🏥 Emergency Information
Emergency numbers, nearest hospitals/clinics, embassy/consulate info, travel insurance
reminders, and safety tips for the destination.

## 📱 Useful Apps & Resources
Must-have apps for the destination, offline maps, translation apps, local services.

## 📋 Day-by-Day Quick Reference
A compact reference card for each day: key activities, addresses, reservation confirmations needed.

Return the complete guide in Markdown format."""

    provider = os.getenv("LLM_PROVIDER", "openai").lower().strip()

    try:
        if provider == "anthropic":
            import anthropic
            client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            model = os.getenv("LLM_MODEL", "claude-sonnet-4-20250514")
            response = client.messages.create(
                model=model,
                max_tokens=8000,
                messages=[{"role": "user", "content": prompt}],
            )
            guide_text = response.content[0].text
        elif provider == "gemini":
            # Use OpenAI-compatible endpoint for Gemini
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("GEMINI_API_KEY"),
                           base_url="https://generativelanguage.googleapis.com/v1beta/openai/")
            model = os.getenv("LLM_MODEL", "gemini-2.0-flash")
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=8000,
            )
            guide_text = response.choices[0].message.content
        else:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            model = os.getenv("LLM_MODEL", "gpt-4o-mini")
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=8000,
            )
            guide_text = response.choices[0].message.content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Guide generation failed: {str(e)}")

    return {
        "guide": guide_text,
        "destination": trip.destination,
        "generated_at": datetime.utcnow().isoformat(),
    }


# ── Chat history ───────────────────────────────────────────────────────────

@app.get("/trips/{trip_id}/chat/history")
def get_chat_history(trip_id: str, user_id: str):
    """Return the conversation history for a trip's itinerary chat."""
    db = get_db()
    trip = db.query(Trip).filter(Trip.id == trip_id, Trip.user_id == user_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    messages = db.query(ChatMessage).filter(
        ChatMessage.trip_id == trip_id
    ).order_by(ChatMessage.created_at).all()

    return {
        "messages": [
            {"role": m.role, "content": m.content, "created_at": m.created_at.isoformat()}
            for m in messages
        ]
    }


# Search endpoints
@app.get("/pinterest")
async def pinterest_images(
    city: str = Query(..., description="City name"),
    country: str = Query(..., description="Country name"),
    region: str = Query("", description="Region/state name"),
):
    """Fetch Pinterest-style travel images for a city."""
    from pinterest_dl import PinterestDL

    if city == "Mock" and country == "United States":
        batch_id = "mock"
        download_dir = os.path.join(PINTEREST_DIR, batch_id)
        image_files = sorted(os.listdir(download_dir))
        return [f"/pinterest/{batch_id}/{fname}" for fname in image_files]

    parts = [city] + ([region] if region else []) + [country]
    query = f"photos of {' '.join(parts)}"
    batch_id = uuid.uuid4().hex[:8]
    download_dir = os.path.join(PINTEREST_DIR, batch_id)
    os.makedirs(download_dir, exist_ok=True)
    try:
        PinterestDL.with_api().search_and_download(
            query=query,
            output_dir=download_dir,
            num=20,
        )
        image_files = sorted(os.listdir(download_dir))
        return [f"/pinterest/{batch_id}/{fname}" for fname in image_files]
    except Exception as e:
        shutil.rmtree(download_dir, ignore_errors=True)
        raise HTTPException(status_code=502, detail=str(e))


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

# Vibe endpoint
class VibeRequest(BaseModel):
    upvoted: List[str]
    downvoted: List[str] = []

@app.post("/vibe")
def get_vibe(request: VibeRequest):
    """Generate a short trip-vibe description from upvoted/downvoted image paths."""
    from vibe_generator import generate_vibe

    def resolve(path: str) -> str:
        """Convert a /pinterest/... URL path to its filesystem location."""
        if path.startswith("/pinterest/"):
            return os.path.join(PINTEREST_DIR, path[len("/pinterest/"):])
        return path

    try:
        vibe = generate_vibe(
            [resolve(p) for p in request.upvoted],
            [resolve(p) for p in request.downvoted],
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=f"Image not found: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vibe generation failed: {e}")
    return {"vibe": vibe}


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
            "LocalExpert",
            "FlightFinder",
            "AccommodationFinder",
            "LocalTravelAdvisor",
            "ItineraryPlanner",
        ],
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
