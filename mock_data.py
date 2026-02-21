"""
Mock data for flights and hotels - simulates external API responses
"""
import random
from datetime import datetime, timedelta

# Mock airline data
AIRLINES = {
    "AA": "American Airlines",
    "DL": "Delta Air Lines",
    "UA": "United Airlines",
    "LH": "Lufthansa",
    "BA": "British Airways",
    "AF": "Air France",
    "KL": "KLM",
    "EK": "Emirates",
    "QR": "Qatar Airways",
    "JL": "Japan Airlines",
    "SQ": "Singapore Airlines",
    "CX": "Cathay Pacific",
    "AY": "Finnair",
    "IB": "Iberia",
    "VS": "Virgin Atlantic"
}

# Airport codes mapping
AIRPORTS = {
    "Tokyo": ["NRT", "HND"],
    "Paris": ["CDG", "ORY"],
    "London": ["LHR", "LGW", "STN"],
    "New York": ["JFK", "LGA", "EWR"],
    "Barcelona": ["BCN"],
    "Rome": ["FCO", "CIA"],
    "Bangkok": ["BKK", "DMK"],
    "Dubai": ["DXB"],
    "Singapore": ["SIN"],
    "Sydney": ["SYD"],
    "Istanbul": ["IST", "SAW"],
    "Kyoto": ["KIX", "ITM"],
    "Amsterdam": ["AMS"],
    "Berlin": ["BER"],
    "Prague": ["PRG"],
    "Los Angeles": ["LAX"],
    "San Francisco": ["SFO"],
    "Chicago": ["ORD"],
    "Miami": ["MIA"],
    "Boston": ["BOS"],
}

# Mock hotel data by city
HOTEL_TEMPLATES = {
    "Tokyo": [
        ("Hotel Gracery Shinjuku", 4.0, 120, ["wifi", "restaurant"]),
        ("Park Hyatt Tokyo", 5.0, 450, ["wifi", "pool", "spa", "gym"]),
        ("Capsule Hotel Anshin Oyado", 3.0, 35, ["wifi"]),
        ("Shibuya Excel Hotel Tokyu", 4.0, 180, ["wifi", "restaurant"]),
        ("9 Hours Narita", 3.0, 45, ["wifi"]),
    ],
    "Paris": [
        ("Hotel Malte Opera", 4.0, 200, ["wifi", "breakfast"]),
        ("Le Meurice", 5.0, 800, ["wifi", "spa", "pool", "gym"]),
        ("Generator Paris", 3.0, 60, ["wifi", "kitchen"]),
        ("Hotel du Louvre", 4.0, 280, ["wifi", "restaurant", "gym"]),
        ("St Christopher's Inn", 2.5, 45, ["wifi", "kitchen"]),
    ],
    "London": [
        ("The Strand Palace", 4.0, 180, ["wifi", "restaurant"]),
        ("The Savoy", 5.0, 600, ["wifi", "spa", "pool", "gym"]),
        ("Generator London", 3.0, 55, ["wifi", "kitchen"]),
        ("Hub by Premier Inn", 3.5, 100, ["wifi"]),
        ("YHA London Central", 3.0, 40, ["wifi", "kitchen"]),
    ],
    "New York": [
        ("The New Yorker", 4.0, 220, ["wifi", "gym"]),
        ("The Plaza", 5.0, 750, ["wifi", "spa", "pool", "gym"]),
        ("HI NYC Hostel", 3.0, 50, ["wifi", "kitchen"]),
        ("Arlo SoHo", 4.0, 200, ["wifi", "restaurant"]),
        ("Pod 51", 3.5, 90, ["wifi"]),
    ],
    "Barcelona": [
        ("Hotel Barcelona Universal", 4.0, 150, ["wifi", "pool", "gym"]),
        ("W Barcelona", 5.0, 400, ["wifi", "spa", "pool", "gym"]),
        ("Kabul Party Hostel", 3.0, 35, ["wifi", "kitchen"]),
        ("Hotel 1898", 4.0, 200, ["wifi", "spa", "pool"]),
        ("Generator Barcelona", 3.0, 50, ["wifi", "kitchen"]),
    ],
    "Rome": [
        ("Hotel Artis", 3.5, 100, ["wifi", "breakfast"]),
        ("Hotel Eden", 5.0, 550, ["wifi", "spa", "gym"]),
        ("The Beehive", 3.0, 70, ["wifi", "kitchen"]),
        ("Hotel de Russie", 5.0, 500, ["wifi", "spa", "gym"]),
        ("Generator Rome", 3.0, 45, ["wifi", "kitchen"]),
    ],
    "Bangkok": [
        ("Lub d Bangkok Silom", 3.5, 35, ["wifi", "pool"]),
        ("Mandarin Oriental", 5.0, 400, ["wifi", "spa", "pool", "gym"]),
        ("Mad Monkey Hostel", 3.0, 20, ["wifi", "pool", "kitchen"]),
        ("Chatrium Hotel Riverside", 4.5, 80, ["wifi", "pool", "gym"]),
        ("The Yard Hostel", 3.0, 25, ["wifi", "kitchen"]),
    ],
    "Dubai": [
        ("Rove Downtown Dubai", 4.0, 120, ["wifi", "pool", "gym"]),
        ("Burj Al Arab", 5.0, 900, ["wifi", "spa", "pool", "gym"]),
        ("At The Top Hostel", 3.0, 40, ["wifi", "pool"]),
        ("Atlantis The Palm", 5.0, 400, ["wifi", "spa", "waterpark", "gym"]),
        ("Holiday Inn Express", 3.5, 70, ["wifi", "pool"]),
    ],
    "Singapore": [
        ("Hotel 81", 3.0, 60, ["wifi"]),
        ("Marina Bay Sands", 5.0, 450, ["wifi", "spa", "pool", "gym"]),
        ("Beary Best Hostel", 3.0, 35, ["wifi", "kitchen"]),
        ("The Fullerton Hotel", 5.0, 350, ["wifi", "pool", "gym"]),
        ("5footway.inn", 3.0, 50, ["wifi"]),
    ],
    "Sydney": [
        ("Wake Up! Sydney Central", 3.5, 45, ["wifi", "kitchen"]),
        ("Park Hyatt Sydney", 5.0, 600, ["wifi", "spa", "pool", "gym"]),
        ("Zara Tower", 4.0, 150, ["wifi", "gym"]),
        ("Sydney Harbour YHA", 3.5, 55, ["wifi", "kitchen", "pool"]),
        ("Meriton Suites", 4.5, 180, ["wifi", "pool", "gym"]),
    ],
}

# Default hotels for cities not in the list
DEFAULT_HOTELS = [
    ("City Center Hotel", 4.0, 120, ["wifi", "restaurant"]),
    ("Grand Luxury Hotel", 5.0, 350, ["wifi", "spa", "pool", "gym"]),
    ("Backpackers Hostel", 2.5, 30, ["wifi", "kitchen"]),
    ("Boutique Hotel", 4.0, 150, ["wifi", "breakfast"]),
    ("Budget Inn", 3.0, 60, ["wifi"]),
]

def get_airport_for_city(city_name):
    """Get airport code for a city"""
    for city, airports in AIRPORTS.items():
        if city.lower() in city_name.lower() or city_name.lower() in city.lower():
            return airports[0]
    return "XXX"  # Unknown

def generate_mock_flights(from_city, to_city, departure_date, return_date=None, num_travelers=1):
    """Generate mock flight options"""
    from_airport = get_airport_for_city(from_city)
    to_airport = get_airport_for_city(to_city)
    
    flights = []
    
    # Generate 3-5 outbound flight options
    base_price = random.randint(200, 800)
    
    for i in range(random.randint(3, 5)):
        airline_code = random.choice(list(AIRLINES.keys()))
        airline = AIRLINES[airline_code]
        flight_num = f"{airline_code}{random.randint(100, 999)}"
        
        # Departure time variations
        dep_hour = random.randint(6, 22)
        dep_minute = random.choice([0, 15, 30, 45])
        dep_time = f"{dep_hour:02d}:{dep_minute:02d}"
        
        # Duration varies by route (mock)
        duration_hours = random.randint(1, 14)
        duration_mins = random.randint(0, 59)
        
        # Calculate arrival
        dep_datetime = datetime.strptime(f"{departure_date} {dep_time}", "%Y-%m-%d %H:%M")
        arr_datetime = dep_datetime + timedelta(hours=duration_hours, minutes=duration_mins)
        
        price_variation = random.uniform(0.7, 1.4)
        price = round(base_price * price_variation)
        
        flights.append({
            "id": f"flight_out_{i}",
            "flight_type": "outbound",
            "airline": airline,
            "flight_number": flight_num,
            "from_airport": from_airport,
            "to_airport": to_airport,
            "departure_datetime": dep_datetime.isoformat(),
            "arrival_datetime": arr_datetime.isoformat(),
            "duration_minutes": duration_hours * 60 + duration_mins,
            "price": price,
            "currency": "USD",
            "booking_url": f"https://www.{airline.lower().replace(' ', '')}.com/book/{flight_num}",
            "status": "suggested"
        })
    
    # Generate return flights if return date provided
    if return_date:
        for i in range(random.randint(3, 5)):
            airline_code = random.choice(list(AIRLINES.keys()))
            airline = AIRLINES[airline_code]
            flight_num = f"{airline_code}{random.randint(100, 999)}"
            
            dep_hour = random.randint(6, 22)
            dep_minute = random.choice([0, 15, 30, 45])
            dep_time = f"{dep_hour:02d}:{dep_minute:02d}"
            
            duration_hours = random.randint(1, 14)
            duration_mins = random.randint(0, 59)
            
            dep_datetime = datetime.strptime(f"{return_date} {dep_time}", "%Y-%m-%d %H:%M")
            arr_datetime = dep_datetime + timedelta(hours=duration_hours, minutes=duration_mins)
            
            price_variation = random.uniform(0.7, 1.4)
            price = round(base_price * price_variation)
            
            flights.append({
                "id": f"flight_ret_{i}",
                "flight_type": "return",
                "airline": airline,
                "flight_number": flight_num,
                "from_airport": to_airport,
                "to_airport": from_airport,
                "departure_datetime": dep_datetime.isoformat(),
                "arrival_datetime": arr_datetime.isoformat(),
                "duration_minutes": duration_hours * 60 + duration_mins,
                "price": price,
                "currency": "USD",
                "booking_url": f"https://www.{airline.lower().replace(' ', '')}.com/book/{flight_num}",
                "status": "suggested"
            })
    
    return flights

def generate_mock_accommodations(city_name, check_in, check_out, num_guests=1):
    """Generate mock hotel options"""
    hotels = HOTEL_TEMPLATES.get(city_name, DEFAULT_HOTELS)
    
    accommodations = []
    
    for i, (name, rating, base_price, amenities) in enumerate(hotels):
        # Price variation
        price_variation = random.uniform(0.8, 1.3)
        price_per_night = round(base_price * price_variation)
        
        # Calculate nights
        check_in_dt = datetime.strptime(check_in, "%Y-%m-%d")
        check_out_dt = datetime.strptime(check_out, "%Y-%m-%d")
        nights = (check_out_dt - check_in_dt).days
        
        accommodations.append({
            "id": f"acc_{i}",
            "name": name,
            "type": "hotel" if rating >= 3 else "hostel",
            "address": f"{random.randint(1, 200)} Main Street, {city_name}",
            "city": city_name,
            "check_in_date": check_in,
            "check_out_date": check_out,
            "price_per_night": price_per_night,
            "total_price": price_per_night * max(nights, 1),
            "currency": "USD",
            "rating": rating,
            "amenities": amenities,
            "booking_url": f"https://www.booking.com/hotel/{name.lower().replace(' ', '-')}.html",
            "status": "suggested"
        })
    
    return accommodations

def get_city_info(city_name):
    """Get basic info about a city"""
    city_data = {
        "Tokyo": {
            "country": "Japan",
            "description": "A dazzling mix of neon-lit modernity and ancient traditions",
            "top_attractions": ["Senso-ji Temple", "Tokyo Skytree", "Meiji Shrine", "Shibuya Crossing", "Tsukiji Outer Market"],
            "best_food": ["Sushi", "Ramen", "Tempura", "Yakitori", "Tonkatsu"],
            "local_transport": "JR Yamanote Line, Tokyo Metro"
        },
        "Paris": {
            "country": "France",
            "description": "The City of Light, famous for art, fashion, and cuisine",
            "top_attractions": ["Eiffel Tower", "Louvre Museum", "Notre-Dame", "Arc de Triomphe", "Montmartre"],
            "best_food": ["Croissants", "Steak Frites", "Crepes", "Macarons", "French Onion Soup"],
            "local_transport": "Metro, RER, Bus"
        },
        "London": {
            "country": "UK",
            "description": "Historic capital blending royal tradition with modern culture",
            "top_attractions": ["Big Ben", "Tower of London", "British Museum", "London Eye", "Buckingham Palace"],
            "best_food": ["Fish and Chips", "Sunday Roast", "Afternoon Tea", "Curry", "Pie and Mash"],
            "local_transport": "Tube, Bus, Overground"
        },
        "New York": {
            "country": "USA",
            "description": "The city that never sleeps, iconic skyline and diverse culture",
            "top_attractions": ["Statue of Liberty", "Central Park", "Times Square", "Empire State Building", "Brooklyn Bridge"],
            "best_food": ["Pizza", "Bagels", "Cheesecake", "Hot Dogs", "Pastrami Sandwich"],
            "local_transport": "Subway, Bus, Taxi"
        },
        "Barcelona": {
            "country": "Spain",
            "description": "Mediterranean city known for Gaudi architecture and beaches",
            "top_attractions": ["Sagrada Familia", "Park Guell", "La Rambla", "Gothic Quarter", "Casa Batllo"],
            "best_food": ["Tapas", "Paella", "Churros", "Jamón Iberico", "Crema Catalana"],
            "local_transport": "Metro, Bus, Tram"
        },
    }
    
    return city_data.get(city_name, {
        "country": "Unknown",
        "description": f"A beautiful destination waiting to be explored",
        "top_attractions": ["City Center", "Old Town", "Main Square", "Local Market", "Museum"],
        "best_food": ["Local Cuisine", "Street Food", "Traditional Dishes"],
        "local_transport": "Bus, Metro, Taxi"
    })
