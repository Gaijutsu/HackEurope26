"""
Simplified Planning Agent - Uses OpenAI directly with structured prompts
"""
import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
import openai
from mock_data import generate_mock_flights, generate_mock_accommodations, get_city_info

# Set OpenAI API key from environment
openai.api_key = os.getenv("OPENAI_API_KEY", "your-api-key-here")

class PlanningAgent:
    """
    Single agent that handles the entire planning workflow:
    1. Destination research
    2. City selection (if country)
    3. Flight search (mock)
    4. Accommodation search (mock)
    5. Itinerary creation
    """
    
    def __init__(self):
        self.model = "gpt-4o-mini"  # Use mini for faster/cheaper responses
    
    def plan_trip(self, trip_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main planning method - creates a complete trip plan
        """
        destination = trip_data["destination"]
        start_date = trip_data["start_date"]
        end_date = trip_data["end_date"]
        num_travelers = trip_data.get("num_travelers", 1)
        interests = trip_data.get("interests", [])
        dietary = trip_data.get("dietary_restrictions", [])
        budget = trip_data.get("budget_level", "mid")
        
        # Calculate duration
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        duration_days = (end_dt - start_dt).days + 1
        
        # Step 1: Determine if destination is city or country
        is_country = self._is_likely_country(destination)
        
        # Step 2: Get destination info and cities
        if is_country:
            cities = self._select_cities_for_country(destination, duration_days, interests)
        else:
            cities = [destination]
        
        # Step 3: Generate flights (mock)
        # For hackathon, assume user is flying from a default origin
        origin_city = "New York"  # Default origin
        flights = generate_mock_flights(origin_city, cities[0], start_date, end_date, num_travelers)
        
        # Step 4: Generate accommodations (mock)
        accommodations = []
        for city in cities:
            city_acc = generate_mock_accommodations(city, start_date, end_date, num_travelers)
            accommodations.extend(city_acc[:2])  # Top 2 per city
        
        # Step 5: Generate itinerary using AI
        itinerary = self._generate_itinerary(
            cities=cities,
            start_date=start_date,
            end_date=end_date,
            interests=interests,
            dietary=dietary,
            budget=budget
        )
        
        return {
            "cities": cities,
            "flights": flights,
            "accommodations": accommodations,
            "itinerary": itinerary,
            "is_country_level": is_country,
            "planning_summary": f"Planned {duration_days} days in {', '.join(cities)}"
        }
    
    def _is_likely_country(self, destination: str) -> bool:
        """Simple heuristic to determine if destination is a country"""
        countries = ["Japan", "France", "Italy", "Spain", "Thailand", "Germany", "UK", "USA", 
                     "Australia", "Brazil", "India", "China", "Mexico", "Greece", "Turkey",
                     "Vietnam", "Cambodia", "Malaysia", "Indonesia", "Philippines"]
        return destination in countries
    
    def _select_cities_for_country(self, country: str, duration_days: int, interests: List[str]) -> List[str]:
        """Select which cities to visit in a country"""
        
        city_selection_prompt = f"""You are a travel expert. For a trip to {country} lasting {duration_days} days,
select the best cities to visit based on these interests: {', '.join(interests)}.

Return ONLY a JSON array of city names, ordered by visit sequence. Example: ["Tokyo", "Kyoto", "Osaka"]

Rules:
- Select 2-4 cities depending on duration (2-3 days per city minimum)
- Choose cities that match the interests
- Optimize for logical route (minimize backtracking)
- Include the capital or most popular city
"""
        
        try:
            response = openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful travel planning assistant. Return only valid JSON arrays."},
                    {"role": "user", "content": city_selection_prompt}
                ],
                temperature=0.7,
                max_tokens=200
            )
            
            content = response.choices[0].message.content.strip()
            # Extract JSON from response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            cities = json.loads(content)
            if isinstance(cities, list) and len(cities) > 0:
                return cities[:4]  # Max 4 cities
        except Exception as e:
            print(f"Error selecting cities: {e}")
        
        # Fallback: return default cities for known countries
        defaults = {
            "Japan": ["Tokyo", "Kyoto", "Osaka"],
            "France": ["Paris", "Nice", "Lyon"],
            "Italy": ["Rome", "Florence", "Venice"],
            "Spain": ["Barcelona", "Madrid", "Seville"],
            "Thailand": ["Bangkok", "Chiang Mai", "Phuket"],
            "UK": ["London", "Edinburgh", "Manchester"],
            "USA": ["New York", "Los Angeles", "San Francisco"],
            "Germany": ["Berlin", "Munich", "Hamburg"],
        }
        return defaults.get(country, [f"{country} City 1", f"{country} City 2"])
    
    def _generate_itinerary(self, cities: List[str], start_date: str, end_date: str,
                           interests: List[str], dietary: List[str], budget: str) -> List[Dict]:
        """Generate day-by-day itinerary using AI"""
        
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        duration_days = (end_dt - start_dt).days + 1
        
        # Allocate days to cities
        days_per_city = self._allocate_days_to_cities(cities, duration_days)
        
        itinerary = []
        current_date = start_dt
        
        for city_idx, city in enumerate(cities):
            city_days = days_per_city[city_idx]
            city_info = get_city_info(city)
            
            for day in range(city_days):
                date_str = current_date.strftime("%Y-%m-%d")
                day_number = len(itinerary) + 1
                
                # Generate day's activities using AI
                day_plan = self._generate_day_plan(
                    city=city,
                    city_info=city_info,
                    date=date_str,
                    day_number=day_number,
                    interests=interests,
                    dietary=dietary,
                    budget=budget,
                    is_first_day=(day == 0),
                    is_last_day=(day == city_days - 1 and city_idx == len(cities) - 1)
                )
                
                itinerary.append({
                    "day_number": day_number,
                    "date": date_str,
                    "city": city,
                    "items": day_plan
                })
                
                current_date += timedelta(days=1)
        
        return itinerary
    
    def _allocate_days_to_cities(self, cities: List[str], total_days: int) -> List[int]:
        """Allocate days to each city proportionally"""
        num_cities = len(cities)
        base_days = total_days // num_cities
        extra_days = total_days % num_cities
        
        allocation = [base_days] * num_cities
        for i in range(extra_days):
            allocation[i] += 1
        
        return allocation
    
    def _generate_day_plan(self, city: str, city_info: Dict, date: str, day_number: int,
                          interests: List[str], dietary: List[str], budget: str,
                          is_first_day: bool, is_last_day: bool) -> List[Dict]:
        """Generate a single day's plan using AI"""
        
        prompt = f"""Create a detailed daily itinerary for {city}, {city_info['country']} on {date}.

City Info:
- Description: {city_info['description']}
- Top Attractions: {', '.join(city_info['top_attractions'])}
- Best Food: {', '.join(city_info['best_food'])}
- Transport: {city_info['local_transport']}

User Preferences:
- Interests: {', '.join(interests)}
- Dietary Restrictions: {', '.join(dietary) if dietary else 'None'}
- Budget Level: {budget}
- Day Number: {day_number} {'(First day - include arrival/check-in)' if is_first_day else ''} {'(Last day - include departure)' if is_last_day else ''}

Return a JSON array of activities with this structure:
[
  {{
    "start_time": "09:00",
    "duration_minutes": 120,
    "title": "Activity name",
    "description": "Brief description",
    "item_type": "attraction|meal|transport|free_time",
    "location": "Specific location name",
    "cost": 25,
    "notes": "Any special notes"
  }}
]

Guidelines:
- Plan 4-6 activities per day
- Include breakfast, lunch, and dinner
- Respect dietary restrictions when suggesting restaurants
- Mix popular attractions with local experiences
- Include travel time between locations
- Suggest appropriate times (don't schedule dinner at 3pm)
- Budget guide: budget=$10-30/meal, mid=$30-60/meal, luxury=$60+/meal
"""
        
        try:
            response = openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert travel planner. Return only valid JSON arrays with no markdown formatting."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=1500
            )
            
            content = response.choices[0].message.content.strip()
            # Extract JSON from response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            day_plan = json.loads(content)
            if isinstance(day_plan, list):
                # Add IDs and validate
                for i, item in enumerate(day_plan):
                    item["id"] = f"day{day_number}_item{i}"
                    item["status"] = "planned"
                    item["delayed_to_day"] = None
                    item["is_ai_suggested"] = 1
                return day_plan
        except Exception as e:
            print(f"Error generating day plan: {e}")
        
        # Fallback: return basic day plan
        return self._fallback_day_plan(city, day_number)
    
    def _fallback_day_plan(self, city: str, day_number: int) -> List[Dict]:
        """Fallback day plan if AI fails"""
        return [
            {
                "id": f"day{day_number}_item0",
                "start_time": "09:00",
                "duration_minutes": 120,
                "title": f"Explore {city} City Center",
                "description": "Walk around the city center and explore local shops and cafes",
                "item_type": "attraction",
                "location": f"{city} City Center",
                "cost": 0,
                "notes": "Free exploration time",
                "status": "planned",
                "delayed_to_day": None,
                "is_ai_suggested": 1
            },
            {
                "id": f"day{day_number}_item1",
                "start_time": "12:00",
                "duration_minutes": 60,
                "title": "Lunch at Local Restaurant",
                "description": "Enjoy local cuisine at a recommended restaurant",
                "item_type": "meal",
                "location": f"{city} Restaurant District",
                "cost": 25,
                "notes": "Try the local specialties",
                "status": "planned",
                "delayed_to_day": None,
                "is_ai_suggested": 1
            },
            {
                "id": f"day{day_number}_item2",
                "start_time": "14:00",
                "duration_minutes": 180,
                "title": f"Visit {city} Main Attraction",
                "description": "Visit the most popular attraction in the city",
                "item_type": "attraction",
                "location": f"{city} Main Attraction",
                "cost": 20,
                "notes": "Book tickets in advance if possible",
                "status": "planned",
                "delayed_to_day": None,
                "is_ai_suggested": 1
            },
            {
                "id": f"day{day_number}_item3",
                "start_time": "18:00",
                "duration_minutes": 90,
                "title": "Dinner Experience",
                "description": "Enjoy dinner at a local restaurant",
                "item_type": "meal",
                "location": f"{city} Dining Area",
                "cost": 35,
                "notes": "Make reservation recommended",
                "status": "planned",
                "delayed_to_day": None,
                "is_ai_suggested": 1
            }
        ]

# Singleton instance
planning_agent = PlanningAgent()
