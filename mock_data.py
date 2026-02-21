"""
Mock data for flights and hotels - simulates external API responses
"""
import random
from datetime import datetime, timedelta
import traceback

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
    traceback.print_stack()
    print("MOCK DATA USED\nMOCK DATA USED\nMOCK DATA USED\nMOCK DATA USED\nMOCK DATA USED\nMOCK DATA USED\nMOCK DATA USED\nMOCK DATA USED\nMOCK DATA USED\nMOCK DATA USED\nMOCK DATA USED\n")
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
    traceback.print_stack()
    print("MOCK DATA USED\nMOCK DATA USED\nMOCK DATA USED\nMOCK DATA USED\nMOCK DATA USED\nMOCK DATA USED\nMOCK DATA USED\nMOCK DATA USED\nMOCK DATA USED\nMOCK DATA USED\nMOCK DATA USED\n")

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
    """Get basic info about a city including neighbourhood/district layout"""
    city_data = {
        "Tokyo": {
            "country": "Japan",
            "description": "A dazzling mix of neon-lit modernity and ancient traditions",
            "top_attractions": ["Senso-ji Temple", "Tokyo Skytree", "Meiji Shrine", "Shibuya Crossing", "Tsukiji Outer Market"],
            "best_food": ["Sushi", "Ramen", "Tempura", "Yakitori", "Tonkatsu"],
            "local_transport": "JR Yamanote Line, Tokyo Metro",
            "neighbourhood_travel": {
                "_note": "Travel times in minutes between areas (walking / transit)",
                "Shinjuku <-> Shibuya": {"walk": 25, "transit": 5, "line": "JR Yamanote"},
                "Shinjuku <-> Harajuku / Omotesando": {"walk": 20, "transit": 4, "line": "JR Yamanote"},
                "Shibuya <-> Harajuku / Omotesando": {"walk": 15, "transit": 3, "line": "JR Yamanote"},
                "Harajuku / Omotesando <-> Ginza / Tsukiji": {"walk": 50, "transit": 15, "line": "Ginza Line"},
                "Ginza / Tsukiji <-> Asakusa": {"walk": 60, "transit": 15, "line": "Ginza Line"},
                "Asakusa <-> Ueno": {"walk": 15, "transit": 5, "line": "Ginza Line"},
                "Ueno <-> Akihabara": {"walk": 12, "transit": 3, "line": "JR Yamanote"},
                "Akihabara <-> Ginza / Tsukiji": {"walk": 25, "transit": 8, "line": "Hibiya Line"},
                "Shinjuku <-> Akihabara": {"walk": 70, "transit": 15, "line": "JR Chuo"},
                "Shibuya <-> Ginza / Tsukiji": {"walk": 55, "transit": 15, "line": "Ginza Line"}
            },
            "suggested_routes": [
                {"type": "loop", "name": "West Tokyo loop", "areas": ["Shinjuku", "Harajuku / Omotesando", "Shibuya", "Shinjuku"], "note": "All walkable, great half-day loop"},
                {"type": "linear", "name": "East Tokyo line", "areas": ["Ueno", "Akihabara", "Ginza / Tsukiji", "Asakusa"], "note": "Take Ginza Line back to hotel"},
                {"type": "linear", "name": "Cross-city day", "areas": ["Shinjuku", "Harajuku / Omotesando", "Ginza / Tsukiji", "Asakusa"], "note": "Take JR Yamanote back from Ueno"}
            ],
            "transit_hubs": ["Shinjuku Station", "Shibuya Station", "Tokyo Station", "Ueno Station"],
            "neighbourhoods": {
                "Shinjuku": {
                    "vibe": "Nightlife, shopping, skyscrapers",
                    "attractions": ["Shinjuku Gyoen", "Golden Gai", "Kabukicho", "Tokyo Metropolitan Government Building"],
                    "food": ["Fuunji Ramen", "Omoide Yokocho yakitori stalls", "Tsunahachi Tempura"]
                },
                "Shibuya": {
                    "vibe": "Youth culture, fashion, nightlife",
                    "attractions": ["Shibuya Crossing", "Hachiko Statue", "Shibuya Sky", "Center Gai"],
                    "food": ["Ichiran Ramen Shibuya", "Genki Sushi Shibuya", "Uobei Sushi"]
                },
                "Asakusa": {
                    "vibe": "Traditional, temples, old Tokyo",
                    "attractions": ["Senso-ji Temple", "Nakamise Shopping Street", "Tokyo Skytree (nearby)"],
                    "food": ["Asakusa Gyukatsu", "Sometaro Okonomiyaki", "Daikokuya Tempura"]
                },
                "Harajuku / Omotesando": {
                    "vibe": "Fashion, cafes, green spaces",
                    "attractions": ["Meiji Shrine", "Takeshita Street", "Omotesando Hills"],
                    "food": ["Harajuku Gyozaro", "Eggs 'n Things", "Afuri Ramen Harajuku"]
                },
                "Ginza / Tsukiji": {
                    "vibe": "Upscale shopping, seafood, galleries",
                    "attractions": ["Tsukiji Outer Market", "Kabuki-za Theatre", "Ginza Six"],
                    "food": ["Sushi Dai", "Tsukiji Tamazushi", "Ginza Kagari Ramen"]
                },
                "Akihabara": {
                    "vibe": "Electronics, anime, otaku culture",
                    "attractions": ["Electric Town", "Anime shops", "Maid cafes"],
                    "food": ["Kanda Matsuya Soba", "CoCo Ichibanya Curry"]
                },
                "Ueno": {
                    "vibe": "Museums, park, cultural hub",
                    "attractions": ["Ueno Park", "Tokyo National Museum", "Ameya-Yokocho Market"],
                    "food": ["Innsyoutei", "Hantei Kushiage"]
                }
            }
        },
        "Paris": {
            "country": "France",
            "description": "The City of Light, famous for art, fashion, and cuisine",
            "top_attractions": ["Eiffel Tower", "Louvre Museum", "Notre-Dame", "Arc de Triomphe", "Montmartre"],
            "best_food": ["Croissants", "Steak Frites", "Crepes", "Macarons", "French Onion Soup"],
            "local_transport": "Metro, RER, Bus",
            "neighbourhood_travel": {
                "_note": "Travel times in minutes between areas (walking / transit)",
                "Le Marais (3rd-4th arr.) <-> Louvre / Les Halles (1st-2nd arr.)": {"walk": 15, "transit": 5, "line": "M1"},
                "Louvre / Les Halles (1st-2nd arr.) <-> Saint-Germain-des-Prés (6th arr.)": {"walk": 15, "transit": 5, "line": "M4"},
                "Saint-Germain-des-Prés (6th arr.) <-> Latin Quarter (5th arr.)": {"walk": 10, "transit": 3, "line": "walk"},
                "Louvre / Les Halles (1st-2nd arr.) <-> Champs-Élysées / Trocadéro (8th/16th arr.)": {"walk": 30, "transit": 8, "line": "M1"},
                "Champs-Élysées / Trocadéro (8th/16th arr.) <-> Montmartre (18th arr.)": {"walk": 45, "transit": 12, "line": "M2"},
                "Le Marais (3rd-4th arr.) <-> Latin Quarter (5th arr.)": {"walk": 20, "transit": 8, "line": "M7"},
                "Le Marais (3rd-4th arr.) <-> Montmartre (18th arr.)": {"walk": 50, "transit": 15, "line": "M12"},
                "Louvre / Les Halles (1st-2nd arr.) <-> Montmartre (18th arr.)": {"walk": 35, "transit": 10, "line": "M4"}
            },
            "suggested_routes": [
                {"type": "loop", "name": "Central Paris loop", "areas": ["Le Marais (3rd-4th arr.)", "Louvre / Les Halles (1st-2nd arr.)", "Saint-Germain-des-Prés (6th arr.)", "Latin Quarter (5th arr.)", "Le Marais (3rd-4th arr.)"], "note": "All walkable, classic Paris walk"},
                {"type": "linear", "name": "Landmarks line", "areas": ["Louvre / Les Halles (1st-2nd arr.)", "Champs-Élysées / Trocadéro (8th/16th arr.)", "Montmartre (18th arr.)"], "note": "Take M2/M12 back"},
                {"type": "loop", "name": "Left Bank loop", "areas": ["Saint-Germain-des-Prés (6th arr.)", "Latin Quarter (5th arr.)", "Le Marais (3rd-4th arr.)", "Louvre / Les Halles (1st-2nd arr.)", "Saint-Germain-des-Prés (6th arr.)"], "note": "Leisurely walk along the Seine"}
            ],
            "transit_hubs": ["Châtelet-Les Halles", "Gare du Nord", "Saint-Lazare", "Montparnasse"],
            "neighbourhoods": {
                "Le Marais (3rd-4th arr.)": {
                    "vibe": "Trendy, historic, LGBTQ-friendly",
                    "attractions": ["Place des Vosges", "Musée Picasso", "Rue des Rosiers"],
                    "food": ["L'As du Fallafel", "Breizh Café", "Chez Janou"]
                },
                "Saint-Germain-des-Prés (6th arr.)": {
                    "vibe": "Literary cafes, boutiques, intellectual",
                    "attractions": ["Jardin du Luxembourg", "Saint-Sulpice"],
                    "food": ["Café de Flore", "Les Deux Magots", "Le Bouillon Racine"]
                },
                "Montmartre (18th arr.)": {
                    "vibe": "Artistic, hilltop village, bohemian",
                    "attractions": ["Sacré-Cœur", "Place du Tertre", "Moulin Rouge"],
                    "food": ["Le Consulat", "Pink Mamma", "La Maison Rose"]
                },
                "Latin Quarter (5th arr.)": {
                    "vibe": "Student district, bookshops, bistros",
                    "attractions": ["Panthéon", "Shakespeare and Company", "Jardin des Plantes"],
                    "food": ["Le Bouillon Chartier", "Chez René", "Odette Paris"]
                },
                "Champs-Élysées / Trocadéro (8th/16th arr.)": {
                    "vibe": "Grand boulevards, luxury, landmarks",
                    "attractions": ["Arc de Triomphe", "Eiffel Tower", "Palais de Tokyo"],
                    "food": ["Le Relais de l'Entrecôte", "Ladurée Champs-Élysées"]
                },
                "Louvre / Les Halles (1st-2nd arr.)": {
                    "vibe": "Central, museums, shopping",
                    "attractions": ["Louvre Museum", "Palais Royal", "Les Halles"],
                    "food": ["Stohrer", "Bistrot Benoit", "Au Pied de Cochon"]
                }
            }
        },
        "London": {
            "country": "UK",
            "description": "Historic capital blending royal tradition with modern culture",
            "top_attractions": ["Big Ben", "Tower of London", "British Museum", "London Eye", "Buckingham Palace"],
            "best_food": ["Fish and Chips", "Sunday Roast", "Afternoon Tea", "Curry", "Pie and Mash"],
            "local_transport": "Tube, Bus, Overground",
            "neighbourhood_travel": {
                "_note": "Travel times in minutes between areas (walking / transit)",
                "Westminster / South Bank <-> The City / Tower": {"walk": 30, "transit": 10, "line": "District/Circle"},
                "Westminster / South Bank <-> Bloomsbury / Covent Garden": {"walk": 25, "transit": 8, "line": "Northern Line"},
                "Bloomsbury / Covent Garden <-> Soho / Mayfair": {"walk": 10, "transit": 3, "line": "walk"},
                "Soho / Mayfair <-> South Kensington / Chelsea": {"walk": 35, "transit": 10, "line": "Piccadilly"},
                "The City / Tower <-> Shoreditch / Brick Lane": {"walk": 15, "transit": 5, "line": "Overground"},
                "Bloomsbury / Covent Garden <-> The City / Tower": {"walk": 25, "transit": 8, "line": "Central Line"},
                "Westminster / South Bank <-> Soho / Mayfair": {"walk": 20, "transit": 5, "line": "Jubilee"},
                "Soho / Mayfair <-> Bloomsbury / Covent Garden": {"walk": 10, "transit": 3, "line": "walk"}
            },
            "suggested_routes": [
                {"type": "loop", "name": "Central London loop", "areas": ["Westminster / South Bank", "Bloomsbury / Covent Garden", "Soho / Mayfair", "Westminster / South Bank"], "note": "Walkable riverside loop"},
                {"type": "linear", "name": "East London line", "areas": ["Bloomsbury / Covent Garden", "The City / Tower", "Shoreditch / Brick Lane"], "note": "Take Overground or bus back"},
                {"type": "linear", "name": "Museum mile", "areas": ["South Kensington / Chelsea", "Soho / Mayfair", "Bloomsbury / Covent Garden"], "note": "Walk or take Piccadilly Line"}
            ],
            "transit_hubs": ["King's Cross St Pancras", "Waterloo", "Liverpool Street", "Paddington"],
            "neighbourhoods": {
                "Westminster / South Bank": {
                    "vibe": "Landmarks, government, river views",
                    "attractions": ["Big Ben", "London Eye", "Westminster Abbey", "Tate Modern"],
                    "food": ["Regency Café", "Padella (Borough Market)", "The Table Café"]
                },
                "The City / Tower": {
                    "vibe": "Historic core, financial district",
                    "attractions": ["Tower of London", "St Paul's Cathedral", "Sky Garden"],
                    "food": ["Duck & Waffle", "Ye Olde Cheshire Cheese"]
                },
                "Bloomsbury / Covent Garden": {
                    "vibe": "Museums, theatres, bookshops",
                    "attractions": ["British Museum", "Covent Garden Piazza", "Sir John Soane's Museum"],
                    "food": ["Dishoom Covent Garden", "Flat Iron Steak", "Monmouth Coffee"]
                },
                "Soho / Mayfair": {
                    "vibe": "Dining, nightlife, luxury shopping",
                    "attractions": ["Carnaby Street", "Chinatown", "Burlington Arcade"],
                    "food": ["Bao Soho", "Koya Bar", "Bar Italia"]
                },
                "South Kensington / Chelsea": {
                    "vibe": "Museums, elegant residential",
                    "attractions": ["V&A Museum", "Natural History Museum", "Science Museum"],
                    "food": ["Daquise", "Comptoir Libanais"]
                },
                "Shoreditch / Brick Lane": {
                    "vibe": "Street art, markets, hipster",
                    "attractions": ["Brick Lane Market", "Spitalfields Market", "Street Art Tour"],
                    "food": ["Beigel Bake", "Dishoom Shoreditch", "Smokestak"]
                }
            }
        },
        "New York": {
            "country": "USA",
            "description": "The city that never sleeps, iconic skyline and diverse culture",
            "top_attractions": ["Statue of Liberty", "Central Park", "Times Square", "Empire State Building", "Brooklyn Bridge"],
            "best_food": ["Pizza", "Bagels", "Cheesecake", "Hot Dogs", "Pastrami Sandwich"],
            "local_transport": "Subway, Bus, Taxi",
            "neighbourhood_travel": {
                "_note": "Travel times in minutes between areas (walking / transit)",
                "Midtown Manhattan <-> Upper West Side / Central Park": {"walk": 25, "transit": 8, "line": "1/2/3 subway"},
                "Midtown Manhattan <-> SoHo / Greenwich Village": {"walk": 30, "transit": 10, "line": "1 subway"},
                "SoHo / Greenwich Village <-> Lower Manhattan / FiDi": {"walk": 20, "transit": 8, "line": "1 subway"},
                "Lower Manhattan / FiDi <-> Williamsburg (Brooklyn)": {"walk": 40, "transit": 15, "line": "J/M/Z subway"},
                "SoHo / Greenwich Village <-> Williamsburg (Brooklyn)": {"walk": 50, "transit": 15, "line": "L subway"},
                "Midtown Manhattan <-> Lower Manhattan / FiDi": {"walk": 50, "transit": 15, "line": "2/3 express"},
                "Upper West Side / Central Park <-> SoHo / Greenwich Village": {"walk": 50, "transit": 15, "line": "1 subway"}
            },
            "suggested_routes": [
                {"type": "linear", "name": "Downtown to Midtown", "areas": ["Lower Manhattan / FiDi", "SoHo / Greenwich Village", "Midtown Manhattan"], "note": "Walk north through Manhattan"},
                {"type": "loop", "name": "Midtown & Park loop", "areas": ["Midtown Manhattan", "Upper West Side / Central Park", "Midtown Manhattan"], "note": "Walk through Central Park"},
                {"type": "linear", "name": "Brooklyn adventure", "areas": ["Lower Manhattan / FiDi", "Williamsburg (Brooklyn)"], "note": "Walk Brooklyn Bridge, subway back"}
            ],
            "transit_hubs": ["Penn Station", "Grand Central", "Times Square-42nd St", "Fulton Center"],
            "neighbourhoods": {
                "Midtown Manhattan": {
                    "vibe": "Skyscrapers, Broadway, iconic landmarks",
                    "attractions": ["Times Square", "Empire State Building", "Rockefeller Center", "Bryant Park"],
                    "food": ["Joe's Pizza", "Katz's Delicatessen (LES, nearby)", "Los Tacos No.1"]
                },
                "Lower Manhattan / FiDi": {
                    "vibe": "Historic, finance, waterfront",
                    "attractions": ["Statue of Liberty (ferry)", "9/11 Memorial", "Wall Street", "Brooklyn Bridge"],
                    "food": ["Fraunces Tavern", "Two Hands", "Prince Street Pizza"]
                },
                "Upper West Side / Central Park": {
                    "vibe": "Green spaces, museums, residential",
                    "attractions": ["Central Park", "American Museum of Natural History", "Lincoln Center"],
                    "food": ["Jacob's Pickles", "Levain Bakery", "Barney Greengrass"]
                },
                "SoHo / Greenwich Village": {
                    "vibe": "Shopping, galleries, bohemian",
                    "attractions": ["Washington Square Park", "SoHo cast-iron buildings"],
                    "food": ["Balthazar", "Dominique Ansel Bakery", "Mamoun's Falafel"]
                },
                "Williamsburg (Brooklyn)": {
                    "vibe": "Hipster, street art, waterfront",
                    "attractions": ["Brooklyn Bridge Park (nearby)", "Domino Park", "street art"],
                    "food": ["Peter Luger Steak House", "Smorgasburg (weekends)", "SEY Coffee"]
                }
            }
        },
        "Barcelona": {
            "country": "Spain",
            "description": "Mediterranean city known for Gaudi architecture and beaches",
            "top_attractions": ["Sagrada Familia", "Park Guell", "La Rambla", "Gothic Quarter", "Casa Batllo"],
            "best_food": ["Tapas", "Paella", "Churros", "Jamón Ibérico", "Crema Catalana"],
            "local_transport": "Metro, Bus, Tram",
            "neighbourhood_travel": {
                "_note": "Travel times in minutes between areas (walking / transit)",
                "Gothic Quarter (Barri Gòtic) <-> El Born": {"walk": 10, "transit": 3, "line": "walk"},
                "Gothic Quarter (Barri Gòtic) <-> Eixample": {"walk": 15, "transit": 5, "line": "L3"},
                "El Born <-> Barceloneta": {"walk": 10, "transit": 3, "line": "L4"},
                "Eixample <-> Gràcia": {"walk": 20, "transit": 5, "line": "L3"},
                "Gothic Quarter (Barri Gòtic) <-> Barceloneta": {"walk": 15, "transit": 5, "line": "L4"},
                "El Born <-> Eixample": {"walk": 20, "transit": 8, "line": "L1"},
                "Gràcia <-> Gothic Quarter (Barri Gòtic)": {"walk": 35, "transit": 12, "line": "L3"}
            },
            "suggested_routes": [
                {"type": "loop", "name": "Old City loop", "areas": ["Gothic Quarter (Barri Gòtic)", "El Born", "Barceloneta", "Gothic Quarter (Barri Gòtic)"], "note": "All walkable, half-day"},
                {"type": "linear", "name": "Gaudí trail", "areas": ["Gothic Quarter (Barri Gòtic)", "Eixample", "Gràcia"], "note": "Take L3 back from Gràcia"},
                {"type": "loop", "name": "Full city loop", "areas": ["Gothic Quarter (Barri Gòtic)", "Eixample", "Gràcia", "Eixample", "El Born", "Gothic Quarter (Barri Gòtic)"], "note": "Full day with metro help"}
            ],
            "transit_hubs": ["Plaça Catalunya", "Passeig de Gràcia", "Sants Estació", "Arc de Triomf"],
            "neighbourhoods": {
                "Gothic Quarter (Barri Gòtic)": {
                    "vibe": "Medieval streets, historic, central",
                    "attractions": ["Barcelona Cathedral", "Plaça Reial", "Roman ruins"],
                    "food": ["Bar Cañete", "Milk Bar & Bistro", "La Boqueria Market (nearby)"]
                },
                "Eixample": {
                    "vibe": "Modernist architecture, grid layout, upscale",
                    "attractions": ["Sagrada Familia", "Casa Batlló", "Casa Milà (La Pedrera)"],
                    "food": ["Cervecería Catalana", "Tapas 24", "Parking Pizza"]
                },
                "El Born": {
                    "vibe": "Trendy, artisan shops, nightlife",
                    "attractions": ["Picasso Museum", "Basílica de Santa Maria del Mar", "Parc de la Ciutadella"],
                    "food": ["El Xampanyet", "Cal Pep", "Paradiso Bar"]
                },
                "Gràcia": {
                    "vibe": "Bohemian, local feel, plazas",
                    "attractions": ["Park Güell", "Plaça del Sol", "Mercat de l'Abaceria"],
                    "food": ["La Pepita", "Chivuo's", "Café Godot"]
                },
                "Barceloneta": {
                    "vibe": "Beach, seafood, casual",
                    "attractions": ["Barceloneta Beach", "Port Olímpic", "W Hotel sail building"],
                    "food": ["La Mar Salada", "Can Paixano (La Xampanyeria)", "Restaurante Barceloneta"]
                }
            }
        },
    }

    return city_data.get(city_name, {
        "country": "Unknown",
        "description": f"A beautiful destination waiting to be explored",
        "top_attractions": ["City Center", "Old Town", "Main Square", "Local Market", "Museum"],
        "best_food": ["Local Cuisine", "Street Food", "Traditional Dishes"],
        "local_transport": "Bus, Metro, Taxi",
        "neighbourhoods": {}
    })


# ---------------------------------------------------------------------------
# Local hidden gems mock data
# ---------------------------------------------------------------------------

_LOCAL_GEMS: dict[str, list[dict]] = {
    "Tokyo": [
        {"name": "Yanaka Ginza Shopping Street", "category": "hidden_gem",
         "description": "A charming old-fashioned shopping street in one of Tokyo's last shitamachi (old town) neighbourhoods, untouched by WWII bombing.",
         "why_special": "Locals come here for traditional snacks, handmade crafts, and cat-themed souvenirs. Almost no tourists.",
         "best_for": ["culture", "food", "photography"], "neighborhood": "Yanaka"},
        {"name": "Shimokitazawa", "category": "local_favorite",
         "description": "Tokyo's bohemian neighbourhood packed with vintage shops, indie theatres, and tiny izakayas.",
         "why_special": "Where young Tokyoites actually hang out on weekends — the antithesis of Shibuya.",
         "best_for": ["nightlife", "shopping", "culture"], "neighborhood": "Shimokitazawa"},
        {"name": "Todoroki Valley", "category": "hidden_gem",
         "description": "A secret ravine garden in residential Setagaya — a lush walking trail with a waterfall, just minutes from central Tokyo.",
         "why_special": "Most tourists have never heard of it. A genuine oasis of calm.",
         "best_for": ["nature", "relaxation", "photography"], "neighborhood": "Setagaya"},
        {"name": "Harmonica Yokocho, Kichijoji", "category": "authentic_experience",
         "description": "A maze of tiny post-war alley bars and yakitori stalls where office workers unwind after work.",
         "why_special": "Feels like stepping back to 1960s Tokyo. Shoulder-to-shoulder with locals at the counter.",
         "best_for": ["food", "nightlife", "culture"], "neighborhood": "Kichijoji"},
        {"name": "Nezu Shrine", "category": "hidden_gem",
         "description": "One of Tokyo's oldest shrines with thousands of vermillion torii gates — like Kyoto's Fushimi Inari but without the crowds.",
         "why_special": "Stunning azalea garden in spring. A fraction of the visitors compared to Meiji Shrine.",
         "best_for": ["culture", "photography", "nature"], "neighborhood": "Bunkyo"},
    ],
    "Paris": [
        {"name": "Canal Saint-Martin", "category": "local_favorite",
         "description": "Tree-lined canal with iron footbridges where Parisians picnic, people-watch, and play pétanque.",
         "why_special": "The real social heart of young Paris — far more authentic than the Champs-Élysées.",
         "best_for": ["relaxation", "photography", "food"], "neighborhood": "10th arrondissement"},
        {"name": "Rue Mouffetard Market", "category": "authentic_experience",
         "description": "One of Paris's oldest market streets — cheese mongers, fishmongers, and bakers who've been here for generations.",
         "why_special": "A genuine working market, not a tourist show. Come early morning for the best experience.",
         "best_for": ["food", "culture", "photography"], "neighborhood": "5th arrondissement"},
        {"name": "Parc des Buttes-Chaumont", "category": "hidden_gem",
         "description": "A dramatic park with cliffs, a lake, waterfalls, and a temple perched on a rocky island.",
         "why_special": "Parisians' favourite picnic park — most tourists never leave the central arrondissements to find it.",
         "best_for": ["nature", "relaxation", "photography"], "neighborhood": "19th arrondissement"},
        {"name": "Belleville Street Art Walk", "category": "hidden_gem",
         "description": "A multicultural neighbourhood with incredible street art, authentic Chinese/North African food, and panoramic views of Paris.",
         "why_special": "The most diverse, creative neighbourhood in Paris. Feels nothing like the postcard version of the city.",
         "best_for": ["art", "food", "culture"], "neighborhood": "Belleville"},
        {"name": "Le Comptoir Général", "category": "local_favorite",
         "description": "A hidden bar/cultural space inside a former factory courtyard — part tropical garden, part flea market, part concert venue.",
         "why_special": "The kind of place you'd never find without a local showing you. Ring the doorbell to enter.",
         "best_for": ["nightlife", "culture", "art"], "neighborhood": "10th arrondissement"},
    ],
    "London": [
        {"name": "Columbia Road Flower Market", "category": "authentic_experience",
         "description": "A riot of colour and cockney banter every Sunday morning — London's most photogenic market.",
         "why_special": "The surrounding streets open independent shops only on Sundays. Arrive before 9am for the best experience.",
         "best_for": ["photography", "shopping", "culture"], "neighborhood": "Bethnal Green"},
        {"name": "Maltby Street Market", "category": "hidden_gem",
         "description": "Borough Market's cooler, quieter sibling — artisan food stalls under Victorian railway arches.",
         "why_special": "Where London's chefs shop on Saturdays. No tour groups, just incredible food.",
         "best_for": ["food", "culture"], "neighborhood": "Bermondsey"},
        {"name": "Hampstead Heath & Parliament Hill", "category": "local_favorite",
         "description": "800 acres of ancient heath with wild swimming ponds and the best skyline view of London.",
         "why_special": "Londoners' #1 green escape. The mixed bathing pond is a quintessential local experience.",
         "best_for": ["nature", "relaxation", "photography"], "neighborhood": "Hampstead"},
        {"name": "Leake Street Graffiti Tunnel", "category": "hidden_gem",
         "description": "A legal graffiti tunnel under Waterloo Station where artists paint live — the walls change daily.",
         "why_special": "Banksy curated the first exhibition here. It's completely free and always evolving.",
         "best_for": ["art", "photography", "culture"], "neighborhood": "Waterloo"},
        {"name": "God's Own Junkyard", "category": "hidden_gem",
         "description": "A warehouse stuffed with vintage neon signs from Soho clubs, cinemas, and sex shops — a surreal light show.",
         "why_special": "Instagram-famous among locals but barely known to tourists. Free entry, cash bar.",
         "best_for": ["art", "photography", "nightlife"], "neighborhood": "Walthamstow"},
    ],
    "Barcelona": [
        {"name": "Bunkers del Carmel", "category": "local_favorite",
         "description": "Civil War-era anti-aircraft bunkers on a hilltop with a 360° panorama of Barcelona — the city's worst-kept secret.",
         "why_special": "Where locals bring wine at sunset. Far better views than Park Güell, completely free.",
         "best_for": ["photography", "relaxation", "history"], "neighborhood": "El Carmel"},
        {"name": "Mercat de Sant Antoni", "category": "authentic_experience",
         "description": "A beautifully restored 19th-century market where locals buy their weekly produce — plus a Sunday book market outside.",
         "why_special": "The food hall is spectacular and prices are local, not tourist. The bar inside does great vermouth.",
         "best_for": ["food", "culture", "shopping"], "neighborhood": "Sant Antoni"},
        {"name": "Poblenou", "category": "hidden_gem",
         "description": "A former industrial district turned creative hub with street art, co-working cafes, and Barcelona's best craft beer scene.",
         "why_special": "The neighbourhood most locals recommend to friends visiting. Feels like a different city from the Ramblas.",
         "best_for": ["art", "food", "nightlife"], "neighborhood": "Poblenou"},
        {"name": "El Xampanyet & El Born Wine Bars", "category": "authentic_experience",
         "description": "Tiny, tiled standing bars where you drink cava and eat anchovies like a local. No seats, no fuss.",
         "why_special": "These family-run bars have barely changed in 50 years. The cava is €2 a glass.",
         "best_for": ["food", "nightlife", "culture"], "neighborhood": "El Born"},
    ],
    "New York": [
        {"name": "Roosevelt Island Tramway", "category": "hidden_gem",
         "description": "An aerial tramway over the East River with stunning Manhattan views — and it costs just a MetroCard swipe.",
         "why_special": "One of the best views of the skyline for the price of a subway ride. Almost no tourists.",
         "best_for": ["photography", "adventure"], "neighborhood": "Roosevelt Island"},
        {"name": "Red Hook, Brooklyn", "category": "local_favorite",
         "description": "A waterfront neighbourhood with artist studios, a community farm, and legendary ball fields food vendors on weekends.",
         "why_special": "The ball fields serve some of the best Latin American street food in the city. Deliberately hard to reach — no subway.",
         "best_for": ["food", "art", "culture"], "neighborhood": "Red Hook"},
        {"name": "The Cloisters", "category": "hidden_gem",
         "description": "A medieval European monastery reassembled stone-by-stone in a park overlooking the Hudson — a branch of the Met.",
         "why_special": "Feels like being transported to medieval France. Most tourists never make it this far uptown.",
         "best_for": ["art", "history", "nature"], "neighborhood": "Fort Tryon Park"},
        {"name": "Smorgasburg Williamsburg", "category": "authentic_experience",
         "description": "A massive open-air food market every weekend with 100+ vendors — the best of Brooklyn's food scene in one place.",
         "why_special": "Where food trends are born. Locals treat it as a weekly ritual.",
         "best_for": ["food", "culture", "photography"], "neighborhood": "Williamsburg"},
    ],
    "Rome": [
        {"name": "Testaccio Market & Neighbourhood", "category": "local_favorite",
         "description": "Rome's most authentic food neighbourhood — the covered market has stalls run by the same families for generations.",
         "why_special": "Where Romans actually eat. Try supplì, trapizzino, and offal dishes you won't find in the centro storico.",
         "best_for": ["food", "culture"], "neighborhood": "Testaccio"},
        {"name": "Aventine Keyhole", "category": "hidden_gem",
         "description": "A tiny keyhole in a door on Aventine Hill that perfectly frames St Peter's dome through a garden of orange trees.",
         "why_special": "Rome's most magical free experience. Queue is short — most tourists don't know about it.",
         "best_for": ["photography", "culture"], "neighborhood": "Aventine Hill"},
        {"name": "Trastevere Back Streets", "category": "authentic_experience",
         "description": "Skip the main piazzas and wander the residential back streets for family-run trattorias with paper tablecloths.",
         "why_special": "The deeper you go into Trastevere, the better (and cheaper) the food gets.",
         "best_for": ["food", "culture", "photography"], "neighborhood": "Trastevere"},
    ],
}

_DEFAULT_LOCAL_GEMS = [
    {"name": "Local Market District", "category": "authentic_experience",
     "description": "The city's main local market where residents do their daily shopping.",
     "why_special": "A window into everyday local life, far from tourist areas.",
     "best_for": ["food", "culture"], "neighborhood": "City Center"},
    {"name": "University Quarter", "category": "local_favorite",
     "description": "The area around the local university — cheap eats, indie shops, and young energy.",
     "why_special": "Where locals in their 20s and 30s actually spend their time.",
     "best_for": ["food", "nightlife", "culture"], "neighborhood": "University District"},
    {"name": "Old Artisan Quarter", "category": "hidden_gem",
     "description": "A neighbourhood of traditional workshops, small galleries, and family-run cafes.",
     "why_special": "Most guidebooks skip this area entirely.",
     "best_for": ["culture", "art", "shopping"], "neighborhood": "Old Town"},
]


def generate_mock_local_gems(city_name: str, interests: list[str] | None = None) -> list[dict]:
    """Generate mock local hidden gem recommendations for a city."""
    import copy
    gems = copy.deepcopy(_LOCAL_GEMS.get(city_name, _DEFAULT_LOCAL_GEMS))

    # Enrich each gem with Google Maps URL and source
    for gem in gems:
        place = gem["name"]
        city = gem.get("neighborhood", city_name)
        query = f"{place} {city_name}".replace(" ", "+")
        gem["google_maps_url"] = f"https://www.google.com/maps/search/{query}"
        gem["source"] = "Local reviews & travel blogs"

    # If interests provided, sort gems so matching ones come first
    if interests:
        lower_interests = {i.lower() for i in interests}

        def score(g):
            return -len(lower_interests & {b.lower() for b in g.get("best_for", [])})

        gems.sort(key=score)

    return gems


# ---------------------------------------------------------------------------
# Local travel information mock data
# ---------------------------------------------------------------------------

_LOCAL_TRAVEL_INFO: dict[str, dict] = {
    "Tokyo": {
        "transport_apps": [
            {"name": "Suica / Pasmo (IC Card)", "description": "Rechargeable smart card for all trains, subways, and buses. Also works at convenience stores and vending machines. Get one at any JR station.", "type": "essential"},
            {"name": "Google Maps", "description": "Excellent for Tokyo train navigation — shows exact platform numbers and real-time delays.", "type": "essential"},
            {"name": "Navitime / Japan Transit Planner", "description": "More detailed than Google Maps for complex transfers. Shows cheapest vs fastest routes.", "type": "recommended"},
            {"name": "PayPay", "description": "Japan's most popular mobile payment app. Many small restaurants accept only cash or PayPay.", "type": "helpful"},
        ],
        "payment_info": {
            "currency": "JPY (¥)",
            "cash_preferred": True,
            "cards_accepted": "Major hotels and department stores accept credit cards, but many small restaurants and izakayas are cash-only.",
            "tips": "Withdraw cash from 7-Eleven or Japan Post ATMs — they reliably accept foreign cards. Other ATMs often don't.",
        },
        "tipping_customs": "Tipping is NOT customary in Japan and can be considered rude. Service is already included and is excellent.",
        "language_tips": "Learn: Sumimasen (excuse me), Arigatou gozaimasu (thank you), Eigo menu arimasu ka? (English menu?). Most train signage is bilingual.",
        "sim_and_connectivity": "Rent a pocket WiFi at the airport (Global WiFi or iVideo) or buy a prepaid data SIM from Bic Camera. Free WiFi is patchy outside major stations.",
        "local_etiquette": [
            "Remove shoes when entering homes, temples, and some restaurants (look for a raised floor)",
            "Don't eat or drink while walking — it's considered rude",
            "Stand on the left side of escalators in Tokyo (right in Osaka)",
            "Talking on the phone on trains is frowned upon — set it to manner mode",
            "Bow slightly when greeting and thanking people",
        ],
    },
    "Paris": {
        "transport_apps": [
            {"name": "Navigo Easy Card", "description": "Rechargeable transport card for Metro, RER, buses, and trams. Buy at any station. Load single tickets (t+) or day passes.", "type": "essential"},
            {"name": "Île-de-France Mobilités", "description": "Official Paris transport app with real-time Metro/bus arrivals, route planning, and service alerts.", "type": "essential"},
            {"name": "Citymapper", "description": "Excellent multi-modal route planner — combines Metro, walking, bike-share, and ride-hailing options.", "type": "recommended"},
            {"name": "Vélib' (bike-share)", "description": "Paris's public bike-share system with stations everywhere. Download the app and use electric or classic bikes from €3.10/day.", "type": "helpful"},
        ],
        "payment_info": {
            "currency": "EUR (€)",
            "cash_preferred": False,
            "cards_accepted": "Contactless card payment is accepted almost everywhere, including small cafes and market stalls. Visa and Mastercard are universal.",
            "tips": "France is very card-friendly. Even the Metro ticket machines take contactless. Keep a little cash for very small purchases or market vendors.",
        },
        "tipping_customs": "Service is included in all restaurant bills (service compris). Rounding up or leaving €1-2 for good service is appreciated but never expected.",
        "language_tips": "Always start with 'Bonjour' when entering a shop or restaurant — it's considered very rude not to. Key phrases: S'il vous plaît (please), L'addition (the bill), Parlez-vous anglais? (Do you speak English?).",
        "sim_and_connectivity": "Buy a prepaid SIM from Orange, SFR, or Free Mobile at any tabac (tobacco shop) or the airport. EU roaming works for European SIMs. Free WiFi in most cafes.",
        "local_etiquette": [
            "Always say 'Bonjour' and 'Au revoir' when entering and leaving shops",
            "Don't rush meals — lunch is at least an hour, dinner can be two",
            "Dress smart-casual; Parisians rarely wear athleisure outside the gym",
            "Queue properly and don't cut in line — the French take this seriously",
            "Metro: let passengers exit before boarding",
        ],
    },
    "London": {
        "transport_apps": [
            {"name": "Oyster Card / Contactless Bank Card", "description": "Use your contactless debit/credit card directly on Tube, buses, and trains — it auto-caps at the daily rate. No need to buy an Oyster card anymore.", "type": "essential"},
            {"name": "TfL Go", "description": "Official Transport for London app with real-time Tube status, journey planning, and bus arrivals.", "type": "essential"},
            {"name": "Citymapper", "description": "The best London transport app — beloved by locals. Shows walking, Tube, bus, bike, and even boat options.", "type": "essential"},
            {"name": "Santander Cycles", "description": "London's public bike-share (Boris Bikes). £1.65 for 30 min. Great for short hops between areas.", "type": "helpful"},
        ],
        "payment_info": {
            "currency": "GBP (£)",
            "cash_preferred": False,
            "cards_accepted": "London is almost entirely cashless. Contactless payments work everywhere including market stalls and buskers. Buses don't accept cash at all.",
            "tips": "You genuinely don't need cash in London. Your contactless card works on all public transport too.",
        },
        "tipping_customs": "Tip 10-12% in sit-down restaurants if service charge isn't included (check the bill). Don't tip at pubs, cafes, or for takeaway.",
        "language_tips": "English-speaking city. Useful: 'Cheers' means thank you. 'Sorry' is used for everything. 'Mind the gap' — watch the step on the Tube.",
        "sim_and_connectivity": "Buy a prepaid SIM from Three, Vodafone, or EE at the airport or any Carphone Warehouse. Free WiFi on the Tube (Zone 1) and in most cafes.",
        "local_etiquette": [
            "Stand on the right on escalators — walk on the left. This is sacred.",
            "Queue for everything. Cutting the queue is the worst social crime in Britain.",
            "Don't make eye contact on the Tube — read a book or stare at your phone like a local",
            "Pubs close at 11pm on weeknights — last orders at 10:30pm",
            "The phrase 'not bad' means 'very good'",
        ],
    },
    "Barcelona": {
        "transport_apps": [
            {"name": "T-Casual Card (10 trips)", "description": "The best value for tourists — a 10-trip card valid on Metro, bus, tram, and local trains. Buy at any Metro station.", "type": "essential"},
            {"name": "TMB App", "description": "Official Barcelona transport app with Metro maps, real-time bus tracking, and journey planner.", "type": "essential"},
            {"name": "Bicing (residents only) / Donkey Republic", "description": "Bicing is locals-only, but Donkey Republic bike rentals are available via app throughout the city.", "type": "helpful"},
            {"name": "Cabify / FreeNow", "description": "Ride-hailing apps that work well in Barcelona. Often cheaper than regular taxis.", "type": "helpful"},
        ],
        "payment_info": {
            "currency": "EUR (€)",
            "cash_preferred": False,
            "cards_accepted": "Card payment is widely accepted. Small tapas bars and market stalls may prefer cash for small amounts under €5.",
            "tips": "Spain is increasingly card-friendly but carry €20 in cash for small purchases and market stalls.",
        },
        "tipping_customs": "Tipping is not expected in Spain. Leaving small change (€0.50-1) at a bar or rounding up at a restaurant is a nice gesture but never required.",
        "language_tips": "Barcelona is bilingual: Catalan (primary) and Spanish. Locals appreciate 'Gràcies' (Catalan thank you) over 'Gracias'. Most people in tourist areas speak English. Key: Una cerveza, si us plau (a beer, please).",
        "sim_and_connectivity": "Buy a prepaid SIM from Vodafone, Orange, or Movistar at the airport or El Corte Inglés. EU roaming applies for European SIMs. Free WiFi in many cafes and public squares.",
        "local_etiquette": [
            "Lunch is 2-4pm, dinner is 9-11pm — restaurants may not be open outside these hours",
            "Siesta time (2-5pm) means some small shops close",
            "Don't eat on the Metro — it's technically not allowed",
            "Watch for pickpockets on La Rambla and in the Metro — use a front-body bag",
            "Catalans are proud of their identity — calling Barcelona 'Spain' without nuance can be sensitive",
        ],
    },
    "New York": {
        "transport_apps": [
            {"name": "OMNY / Contactless Card", "description": "Tap your contactless bank card or phone directly at Subway turnstiles. Auto-caps at $34/week (like an unlimited pass).", "type": "essential"},
            {"name": "Google Maps / Apple Maps", "description": "Both work excellently for NYC subway navigation with real-time service alerts.", "type": "essential"},
            {"name": "Citymapper", "description": "Superb for NYC — shows Subway, bus, Citi Bike, ferries, and walking directions with real-time data.", "type": "recommended"},
            {"name": "Citi Bike", "description": "NYC's bike-share system. $4.49/single ride or $19/day pass. Stations every few blocks in Manhattan and Brooklyn.", "type": "helpful"},
        ],
        "payment_info": {
            "currency": "USD ($)",
            "cash_preferred": False,
            "cards_accepted": "New York is very card-friendly. Some places are card-only. Street food vendors and some bodegas may be cash-only.",
            "tips": "Most places take cards. Keep $20 in small bills for food carts and tips.",
        },
        "tipping_customs": "Tipping is MANDATORY at restaurants: 18-20% for table service. $1-2 per drink at bars. Tip taxi drivers 15-20%. It's part of workers' wages.",
        "language_tips": "English-speaking city. New York is direct — don't take bluntness personally. 'Standing on line' (not 'in line'). 'Houston Street' is pronounced 'HOW-ston'.",
        "sim_and_connectivity": "Buy a prepaid SIM from T-Mobile or AT&T at the airport or any electronics store. Free WiFi in most cafes, many subway stations, and all public parks (LinkNYC kiosks).",
        "local_etiquette": [
            "Walk fast and stay to the right on sidewalks — don't stop in the middle of the pavement",
            "Don't block the subway doors — move to the center of the car",
            "Tipping 18-20% is not optional — it's how servers earn their living",
            "Jaywalking is normal — cross when safe, not when the light says",
            "Don't eat a pizza slice with a fork — fold it in half, New York style",
        ],
    },
    "Rome": {
        "transport_apps": [
            {"name": "Roma MobilityApp / Tabnet", "description": "Official Rome transport app for Metro (A/B/C lines), buses, and trams. Real-time arrivals and route planning.", "type": "essential"},
            {"name": "BIT Ticket (Single Ride)", "description": "€1.50 for 100 minutes of bus/tram travel or one Metro ride. Buy at tabacchi (tobacco shops) or Metro stations. There's no contactless tap on turnstiles.", "type": "essential"},
            {"name": "FreeNow / Uber", "description": "Taxi apps work in Rome. Regular taxis use meters; always insist on the meter being on.", "type": "helpful"},
        ],
        "payment_info": {
            "currency": "EUR (€)",
            "cash_preferred": False,
            "cards_accepted": "Cards are accepted at most restaurants and shops. Smaller trattorias and street vendors may prefer cash.",
            "tips": "Carry €10-20 in cash for gelato shops, coffee bars, and small purchases.",
        },
        "tipping_customs": "Coperto (cover charge of €1-3/person) is standard at restaurants — this is NOT a tip. Rounding up or leaving €1-2 extra is appreciated but not expected.",
        "language_tips": "Learn: Buongiorno (good morning), Scusi (excuse me), Il conto per favore (the bill please). Coffee at the bar (standing) is much cheaper than at a table.",
        "sim_and_connectivity": "Buy a prepaid SIM from TIM, Vodafone, or Wind at the airport or any tabacchi. EU roaming works for European SIMs. Free WiFi is limited — cafes usually have it.",
        "local_etiquette": [
            "Coffee is drunk standing at the bar — sitting at a table can cost 2-3x more",
            "Dress code for churches: cover shoulders and knees (carry a scarf)",
            "Dinner before 8pm marks you as a tourist — Romans eat at 8:30-9:30pm",
            "Don't sit on the Spanish Steps — it's been illegal since 2019 (€250 fine)",
            "Beware of 'gladiators' and rose sellers near tourist sites — they will demand money for photos",
        ],
    },
}

_DEFAULT_TRAVEL_INFO: dict = {
    "transport_apps": [
        {"name": "Google Maps", "description": "Works well for public transit navigation in most cities worldwide.", "type": "essential"},
        {"name": "Local ride-hailing app", "description": "Check if Uber, Bolt, Grab, or a local equivalent operates in your destination.", "type": "recommended"},
    ],
    "payment_info": {
        "currency": "Local currency",
        "cash_preferred": False,
        "cards_accepted": "Visa and Mastercard are widely accepted in most destinations. Carry some local cash for small vendors.",
        "tips": "Exchange currency at the airport or use a no-fee travel card (Wise, Revolut).",
    },
    "tipping_customs": "Research local tipping customs before your trip — they vary widely by country.",
    "language_tips": "Learn basic greetings in the local language. Translation apps like Google Translate (with offline download) are invaluable.",
    "sim_and_connectivity": "Buy a local prepaid SIM at the airport for data. Alternatively, check if your home carrier offers international roaming packages.",
    "local_etiquette": [
        "Research local customs and dress codes before visiting religious sites",
        "Learn the standard greeting in the local language",
        "Be respectful of local dining customs and meal times",
    ],
}


def generate_mock_local_travel_info(city_name: str) -> dict:
    """Generate mock local travel logistics information for a city."""
    import copy
    return copy.deepcopy(_LOCAL_TRAVEL_INFO.get(city_name, _DEFAULT_TRAVEL_INFO))
