"""
Simplified database for hackathon - SQLite with SQLAlchemy
"""
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import json
import uuid

Base = declarative_base()

def generate_id():
    return str(uuid.uuid4())[:8]

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=generate_id)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    password_hash = Column(String)
    preferences = Column(JSON, default=dict)  # dietary, interests, etc.
    credits = Column(Integer, default=3)  # trip credits — start with 3 free
    created_at = Column(DateTime, default=datetime.utcnow)
    
    trips = relationship("Trip", back_populates="user", cascade="all, delete-orphan")

class Trip(Base):
    __tablename__ = "trips"
    
    id = Column(String, primary_key=True, default=generate_id)
    user_id = Column(String, ForeignKey("users.id"))
    title = Column(String)
    destination = Column(String)  # city or country name
    origin_city = Column(String, default='')  # departure city
    destination_type = Column(String)  # 'city' or 'country'
    start_date = Column(String)  # YYYY-MM-DD
    end_date = Column(String)  # YYYY-MM-DD
    num_travelers = Column(Integer, default=1)
    interests = Column(JSON, default=list)  # ['culture', 'food', 'nature']
    dietary_restrictions = Column(JSON, default=list)
    budget_level = Column(Integer, default=1000)  # total trip budget in USD
    planning_status = Column(String, default='pending')  # pending, in_progress, completed, failed
    plan_data = Column(JSON, default=dict)  # Store the complete AI-generated plan
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="trips")
    itinerary_items = relationship("ItineraryItem", back_populates="trip", cascade="all, delete-orphan")
    flights = relationship("Flight", back_populates="trip", cascade="all, delete-orphan")
    accommodations = relationship("Accommodation", back_populates="trip", cascade="all, delete-orphan")

class ItineraryItem(Base):
    __tablename__ = "itinerary_items"
    
    id = Column(String, primary_key=True, default=generate_id)
    trip_id = Column(String, ForeignKey("trips.id"))
    day_number = Column(Integer)
    title = Column(String)
    description = Column(Text)
    start_time = Column(String)  # HH:MM
    duration_minutes = Column(Integer)
    item_type = Column(String)  # attraction, meal, transport, free_time
    location = Column(String)
    cost = Column(Float, default=0)
    currency = Column(String, default='USD')
    booking_url = Column(String, nullable=True)
    status = Column(String, default='planned')  # planned, completed, skipped, delayed
    delayed_to_day = Column(Integer, nullable=True)
    is_ai_suggested = Column(Integer, default=1)  # 1 = AI, 0 = user added
    
    trip = relationship("Trip", back_populates="itinerary_items")

class Flight(Base):
    __tablename__ = "flights"
    
    id = Column(String, primary_key=True, default=generate_id)
    trip_id = Column(String, ForeignKey("trips.id"))
    flight_type = Column(String)  # outbound, return, internal
    airline = Column(String)
    flight_number = Column(String)
    from_airport = Column(String)
    to_airport = Column(String)
    departure_datetime = Column(String)  # ISO format
    arrival_datetime = Column(String)
    duration_minutes = Column(Integer)
    price = Column(Float)
    currency = Column(String, default='USD')
    booking_url = Column(String)
    status = Column(String, default='suggested')  # suggested, selected, booked
    
    trip = relationship("Trip", back_populates="flights")

class Accommodation(Base):
    __tablename__ = "accommodations"
    
    id = Column(String, primary_key=True, default=generate_id)
    trip_id = Column(String, ForeignKey("trips.id"))
    name = Column(String)
    type = Column(String)  # hotel, hostel, apartment
    address = Column(String)
    city = Column(String)
    check_in_date = Column(String)
    check_out_date = Column(String)
    price_per_night = Column(Float)
    total_price = Column(Float)
    currency = Column(String, default='USD')
    rating = Column(Float, nullable=True)
    amenities = Column(JSON, default=list)
    booking_url = Column(String)
    status = Column(String, default='suggested')  # suggested, selected, booked
    
    trip = relationship("Trip", back_populates="accommodations")

class City(Base):
    __tablename__ = "cities"
    
    id = Column(String, primary_key=True, default=generate_id)
    name = Column(String, index=True)
    country = Column(String)
    iata_code = Column(String, nullable=True)
    popularity_score = Column(Float, default=0.5)

# In-memory cache for simple caching
cache = {}

def get_cache(key):
    return cache.get(key)

def set_cache(key, value, ttl_seconds=300):
    cache[key] = value

def init_db():
    """Initialize the database with some seed data"""
    engine = create_engine("sqlite:///./trip_planner.db", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    
    Session = sessionmaker(bind=engine)
    db = Session()
    
    # Seed some popular cities
    popular_cities = [
        ("Tokyo", "Japan", "NRT"),
        ("Paris", "France", "CDG"),
        ("London", "UK", "LHR"),
        ("New York", "USA", "JFK"),
        ("Barcelona", "Spain", "BCN"),
        ("Rome", "Italy", "FCO"),
        ("Bangkok", "Thailand", "BKK"),
        ("Dubai", "UAE", "DXB"),
        ("Singapore", "Singapore", "SIN"),
        ("Sydney", "Australia", "SYD"),
        ("Istanbul", "Turkey", "IST"),
        ("Kyoto", "Japan", "KIX"),
        ("Amsterdam", "Netherlands", "AMS"),
        ("Berlin", "Germany", "BER"),
        ("Prague", "Czech Republic", "PRG"),
    ]
    
    for name, country, iata in popular_cities:
        if not db.query(City).filter(City.name == name).first():
            db.add(City(name=name, country=country, iata_code=iata))
    
    db.commit()
    db.close()
    
    return engine

def get_db():
    engine = create_engine("sqlite:///./trip_planner.db", connect_args={"check_same_thread": False})
    Session = sessionmaker(bind=engine)
    return Session()
