"""
Streamlit Main App - Entry point with navigation
"""
import streamlit as st
import requests
import json
import time
import io
from datetime import datetime, timedelta

import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from icalendar import Calendar, Event as ICalEvent

# Configure page
st.set_page_config(
    page_title="Agentic Trip Planner",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API URL
API_URL = "http://localhost:8000"

# Initialize session state
if "user" not in st.session_state:
    st.session_state.user = None
if "token" not in st.session_state:
    st.session_state.token = None
if "current_page" not in st.session_state:
    st.session_state.current_page = "login"


# ── Helpers: geocoding & iCal ───────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def geocode_location(location: str, city: str):
    """Geocode a location string with progressive fallbacks.

    Cleans noisy location strings (parentheticals, slashes, ampersands)
    and tries increasingly simpler queries until Nominatim resolves one.
    Rate-limit sleeps live *inside* the cached function so they only fire
    on cache misses — subsequent Streamlit reruns return instantly.

    Returns (lat, lon) or None.
    """
    import re
    import time as _time

    geolocator = Nominatim(user_agent="agentic-trip-planner-v1")

    # ── Build a list of progressively simpler query strings ──────────
    # 1. Strip parenthetical annotations  e.g. "(transit hub)"
    cleaned = re.sub(r'\s*\([^)]*\)', '', location).strip()
    # 2. Strip slash-alternatives          e.g. "Les Halles / Louvre area" → "Les Halles"
    cleaned = re.sub(r'\s*/\s*[^,]+', '', cleaned).strip()

    queries: list[str] = []

    # a) Cleaned string + city context
    queries.append(f"{cleaned}, {city}")

    # b) If "&" present, keep only the first item  e.g. "Sacré-Cœur & Place du Tertre, Montmartre, Paris"
    if '&' in cleaned:
        first_part = cleaned.split('&')[0].strip().rstrip(',')
        comma_parts = cleaned.split(',')
        suffix = ', '.join(p.strip() for p in comma_parts[1:]) if len(comma_parts) > 1 else city
        queries.append(f"{first_part}, {suffix}")

    # c) Drop the specific venue name → area / neighbourhood + city
    comma_parts = cleaned.split(',')
    if len(comma_parts) >= 2:
        queries.append(', '.join(p.strip() for p in comma_parts[1:]))

    # d) Cleaned string alone (no city suffix)
    queries.append(cleaned)

    # e) Original raw string + city (in case cleaning removed something useful)
    raw_with_city = f"{location}, {city}"
    if raw_with_city != queries[0]:
        queries.append(raw_with_city)

    # ── Try each query, respecting Nominatim 1-req/s rate limit ──────
    seen: set[str] = set()
    for q in queries:
        key = q.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        try:
            _time.sleep(1.1)  # rate-limit (only runs on cache miss)
            result = geolocator.geocode(q, timeout=5)
            if result:
                return (result.latitude, result.longitude)
        except Exception:
            continue

    return None


def generate_ical(trip_info: dict, days: list) -> bytes:
    """Generate an iCal (.ics) file from trip itinerary data."""
    cal = Calendar()
    cal.add("prodid", "-//Agentic Trip Planner//EN")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("x-wr-calname", trip_info.get("title", "Trip Itinerary"))

    trip_start = datetime.strptime(trip_info["start_date"], "%Y-%m-%d")

    for day in days:
        day_num = day["day_number"]
        event_date = trip_start + timedelta(days=day_num - 1)

        for item in day.get("items", []):
            ev = ICalEvent()
            ev.add("summary", item["title"])
            ev.add("description", item.get("description", ""))

            try:
                h, m = item["start_time"].split(":")[:2]
                ev_start = event_date.replace(hour=int(h), minute=int(m))
            except (ValueError, IndexError, AttributeError):
                ev_start = event_date.replace(hour=9, minute=0)

            ev.add("dtstart", ev_start)
            ev.add("dtend", ev_start + timedelta(minutes=item.get("duration_minutes", 60)))

            if item.get("location"):
                ev.add("location", item["location"])

            ev.add("uid", f"{item.get('id', 'item')}@agentic-trip-planner")
            cal.add_component(ev)

    return cal.to_ical()


# Sidebar navigation
def sidebar():
    with st.sidebar:
        st.title("✈️ Trip Planner")
        
        if st.session_state.user:
            st.write(f"Welcome, **{st.session_state.user['name']}**!")
            st.divider()
            
            if st.button("🏠 Dashboard", use_container_width=True):
                st.session_state.current_page = "dashboard"
                st.rerun()
            
            if st.button("➕ New Trip", use_container_width=True):
                st.session_state.current_page = "create_trip"
                st.rerun()
            
            st.divider()
            
            if st.button("🚪 Logout", use_container_width=True):
                st.session_state.user = None
                st.session_state.token = None
                st.session_state.current_page = "login"
                st.rerun()
        else:
            st.info("Please login to start planning your trips!")

# Page router
def main():
    sidebar()
    
    if st.session_state.current_page == "login":
        show_login()
    elif st.session_state.current_page == "register":
        show_register()
    elif st.session_state.current_page == "dashboard":
        show_dashboard()
    elif st.session_state.current_page == "create_trip":
        show_create_trip()
    elif st.session_state.current_page == "planning":
        show_planning()
    elif st.session_state.current_page in ("itinerary", "flights", "accommodations", "trip_plan"):
        show_trip_plan()

def show_login():
    st.title("Welcome to Agentic Trip Planner 🤖✈️")
    st.caption("Powered by **CrewAI** multi-agent orchestration")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### Login")
        
        with st.form("login_form"):
            email = st.text_input("Email", placeholder="your@email.com")
            password = st.text_input("Password", type="password")
            
            submitted = st.form_submit_button("Login", use_container_width=True)
            
            if submitted:
                if not email or not password:
                    st.error("Please fill in all fields")
                else:
                    try:
                        response = requests.post(
                            f"{API_URL}/auth/login",
                            json={"email": email, "password": password}
                        )
                        
                        if response.status_code == 200:
                            data = response.json()
                            st.session_state.token = data["access_token"]
                            st.session_state.user = data["user"]
                            st.session_state.current_page = "dashboard"
                            st.success("Login successful!")
                            st.rerun()
                        else:
                            try:
                                detail = response.json().get("detail", "Invalid email or password")
                            except (ValueError, KeyError):
                                detail = f"Login failed (HTTP {response.status_code})"
                            st.error(detail)
                    except requests.exceptions.ConnectionError:
                        st.error("Cannot connect to backend. Is the API server running on port 8000?")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
        
        st.markdown("---")
        st.markdown("Don't have an account?")
        if st.button("Register", use_container_width=True):
            st.session_state.current_page = "register"
            st.rerun()
        
        # Demo credentials
        st.info("💡 **Demo**: Use any email/password to register and login")

def show_register():
    st.title("Create Account 📝")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("register_form"):
            name = st.text_input("Name", placeholder="John Doe")
            email = st.text_input("Email", placeholder="john@example.com")
            password = st.text_input("Password", type="password")
            
            submitted = st.form_submit_button("Create Account", use_container_width=True)
            
            if submitted:
                if not name or not email or not password:
                    st.error("Please fill in all fields")
                else:
                    try:
                        response = requests.post(
                            f"{API_URL}/auth/register",
                            json={"name": name, "email": email, "password": password}
                        )
                        
                        if response.status_code == 200:
                            data = response.json()
                            st.session_state.token = data["access_token"]
                            st.session_state.user = data["user"]
                            st.session_state.current_page = "dashboard"
                            st.success("Account created successfully!")
                            st.rerun()
                        else:
                            try:
                                detail = response.json().get("detail", "Registration failed")
                            except (ValueError, KeyError):
                                detail = f"Registration failed (HTTP {response.status_code})"
                            st.error(detail)
                    except requests.exceptions.ConnectionError:
                        st.error("Cannot connect to backend. Is the API server running on port 8000?")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
        
        st.markdown("---")
        if st.button("Back to Login", use_container_width=True):
            st.session_state.current_page = "login"
            st.rerun()

def show_dashboard():
    if not st.session_state.user:
        st.session_state.current_page = "login"
        st.rerun()
        return
    
    st.title("My Trips 🗺️")
    
    try:
        response = requests.get(
            f"{API_URL}/trips",
            params={"user_id": st.session_state.user["id"]}
        )
        
        if response.status_code == 200:
            trips = response.json()
            
            if not trips:
                st.info("No trips yet! Create your first trip to get started.")
                if st.button("➕ Create Your First Trip", type="primary"):
                    st.session_state.current_page = "create_trip"
                    st.rerun()
            else:
                # Display trips in a grid
                cols = st.columns(2)
                for i, trip in enumerate(trips):
                    with cols[i % 2]:
                        with st.container():
                            st.subheader(trip["title"])
                            st.write(f"📍 {trip['destination']}")
                            st.write(f"📅 {trip['start_date']} to {trip['end_date']}")
                            
                            # Status badge
                            status = trip["planning_status"]
                            if status == "completed":
                                st.success("✅ Planning Complete")
                            elif status == "in_progress":
                                st.info("🔄 Planning...")
                            else:
                                st.warning("⏳ Pending")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("View", key=f"view_{trip['id']}", use_container_width=True):
                                    st.session_state.current_trip_id = trip["id"]
                                    st.session_state.current_page = "trip_plan"
                                    st.rerun()
                            with col2:
                                if st.button("Delete", key=f"del_{trip['id']}", use_container_width=True):
                                    try:
                                        del_response = requests.delete(
                                            f"{API_URL}/trips/{trip['id']}",
                                            params={"user_id": st.session_state.user["id"]}
                                        )
                                        if del_response.status_code == 200:
                                            st.success("Trip deleted!")
                                            st.rerun()
                                    except Exception as e:
                                        st.error(f"Error: {e}")
                            
                            st.divider()
        else:
            st.error("Failed to load trips")
    except Exception as e:
        st.error(f"Error: {str(e)}")

def show_create_trip():
    if not st.session_state.user:
        st.session_state.current_page = "login"
        st.rerun()
        return
    
    st.title("Plan New Trip ✨")
    
    # Progress bar
    progress = st.progress(0)
    
    # Step 1: Destination
    st.header("Step 1: Where do you want to go?")
    
    destination = st.text_input(
        "Destination",
        placeholder="e.g., Tokyo, Japan, Paris, France",
        help="Enter a city or country name"
    )
    
    if destination:
        progress.progress(20)
    
    # Step 2: Dates
    st.header("Step 2: When do you want to travel?")
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date")
    with col2:
        end_date = st.date_input("End Date")
    
    if start_date and end_date:
        if end_date < start_date:
            st.error("End date must be after start date")
        else:
            duration = (end_date - start_date).days + 1
            st.info(f"📅 Trip duration: **{duration} days**")
            progress.progress(40)
    
    # Step 3: Travelers
    st.header("Step 3: Who's traveling?")
    
    num_travelers = st.number_input("Number of travelers", min_value=1, max_value=20, value=1)
    
    progress.progress(60)
    
    # Step 4: Interests
    st.header("Step 4: What are you interested in?")
    
    interests = st.multiselect(
        "Select your interests",
        options=["Culture", "Food", "Nature", "History", "Art", "Nightlife", 
                "Shopping", "Adventure", "Relaxation", "Photography"],
        default=["Culture", "Food"]
    )
    
    progress.progress(80)
    
    # Step 5: Preferences
    st.header("Step 5: Any preferences or restrictions?")
    
    col1, col2 = st.columns(2)
    
    with col1:
        dietary = st.multiselect(
            "Dietary Restrictions",
            options=["Vegetarian", "Vegan", "Halal", "Kosher", "Gluten-free", "Dairy-free", "Nut-free"],
            help="Select any dietary requirements"
        )
    
    with col2:
        budget = st.select_slider(
            "Budget Level",
            options=["budget", "mid", "luxury"],
            value="mid",
            help="budget: $50-150/day, mid: $150-300/day, luxury: $300+/day"
        )
    
    progress.progress(100)
    
    # Create trip button
    st.divider()
    
    if st.button("✨ Generate My Trip Plan", type="primary", use_container_width=True):
        if not destination:
            st.error("Please enter a destination")
        elif end_date < start_date:
            st.error("Please fix the dates")
        else:
            with st.spinner("Creating your trip..."):
                try:
                    trip_data = {
                        "title": f"Trip to {destination}",
                        "destination": destination,
                        "start_date": start_date.strftime("%Y-%m-%d"),
                        "end_date": end_date.strftime("%Y-%m-%d"),
                        "num_travelers": num_travelers,
                        "interests": interests,
                        "dietary_restrictions": dietary,
                        "budget_level": budget
                    }
                    
                    response = requests.post(
                        f"{API_URL}/trips",
                        params={"user_id": st.session_state.user["id"]},
                        json=trip_data
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        st.session_state.current_trip_id = data["id"]
                        st.session_state.current_page = "planning"
                        st.success("Trip created! Starting AI planning...")
                        st.rerun()
                    else:
                        st.error("Failed to create trip")
                except Exception as e:
                    st.error(f"Error: {str(e)}")

def show_planning():
    if not st.session_state.user:
        st.session_state.current_page = "login"
        st.rerun()
        return
    
    trip_id = st.session_state.get("current_trip_id")
    if not trip_id:
        st.error("No trip selected")
        return
    
    st.title("🤖 AI Agents Planning Your Trip...")
    
    # Agent pipeline visual
    AGENTS = [
        ("🔍", "Destination Researcher", "Researching your destination with web search"),
        ("🏙️", "City Selector", "Choosing optimal cities to visit"),
        ("💎", "Local Hidden Gems Expert", "Finding authentic local places beyond tourist traps"),
        ("✈️", "Flight Finder", "Searching for the best flights"),
        ("🏨", "Accommodation Finder", "Finding perfect places to stay"),
        ("🗺️", "Local Travel Advisor", "Compiling local travel tips & apps"),
        ("📅", "Itinerary Planner", "Building your day-by-day plan"),
    ]
    
    try:
        trip_response = requests.get(
            f"{API_URL}/trips/{trip_id}",
            params={"user_id": st.session_state.user["id"]}
        )
        
        if trip_response.status_code == 200:
            trip = trip_response.json()
            st.write(f"### {trip['title']}")
            st.write(f"📍 {trip['destination']} | 📅 {trip['start_date']} to {trip['end_date']}")
            st.divider()
            
            status = trip.get("planning_status", "pending")
            
            if status == "completed":
                st.success("✅ Planning already completed!")
                st.balloons()
                if st.button("📋 View Trip Plan", type="primary", use_container_width=True):
                    st.session_state.current_page = "trip_plan"
                    st.rerun()
                return
            
            # Show agent pipeline
            st.markdown("### 🧠 Agent Pipeline")
            st.caption("Powered by CrewAI")
            
            # Create placeholder containers for each agent
            agent_containers = []
            for icon, name, desc in AGENTS:
                c = st.container()
                with c:
                    cols = st.columns([1, 8, 3])
                    with cols[0]:
                        st.write(icon)
                    with cols[1]:
                        st.write(f"**{name}**")
                        st.caption(desc)
                    with cols[2]:
                        st.write("⏳ Waiting")
                agent_containers.append(c)
            
            st.divider()
            progress_bar = st.progress(0)
            status_text = st.empty()
            log_container = st.expander("📋 Agent Activity Log", expanded=True)
            
            # Use SSE streaming for real-time progress
            status_text.info("🚀 Starting agent pipeline...")
            
            try:
                response = requests.get(
                    f"{API_URL}/trips/{trip_id}/plan/stream",
                    params={"user_id": st.session_state.user["id"]},
                    stream=True,
                    timeout=300,
                )
                
                if response.status_code != 200:
                    # Fallback to sync endpoint
                    status_text.warning("Falling back to synchronous planning...")
                    plan_response = requests.post(
                        f"{API_URL}/trips/{trip_id}/plan",
                        params={"user_id": st.session_state.user["id"]},
                        timeout=300,
                    )
                    if plan_response.status_code == 200:
                        st.success("✅ Planning completed!")
                        st.session_state.current_page = "trip_plan"
                        st.rerun()
                    else:
                        st.error("Planning failed.")
                    return
                
                # Process SSE events
                agent_progress_map = {}  # node_name -> latest status
                log_entries = []
                
                for line in response.iter_lines(decode_unicode=True):
                    if not line or not line.startswith("data: "):
                        continue
                    
                    try:
                        event = json.loads(line[6:])  # strip "data: "
                    except json.JSONDecodeError:
                        continue
                    
                    event_type = event.get("type", event.get("status", ""))
                    
                    if event_type == "error":
                        st.error(f"❌ Error: {event.get('message', 'Unknown error')}")
                        return
                    
                    if event_type == "complete":
                        progress_bar.progress(100)
                        status_text.success("✅ All agents finished! Trip plan ready.")
                        with log_container:
                            st.write(f"✅ **Orchestrator**: Trip planning complete!")
                        time.sleep(1)
                        st.balloons()
                        st.session_state.current_page = "trip_plan"
                        st.rerun()
                        return
                    
                    # Progress event
                    agent_name = event.get("agent", "Unknown")
                    agent_status = event.get("status", "")
                    message = event.get("message", "")
                    
                    # Update progress bar based on agent
                    agent_order = {
                        "DestinationResearcher": 1,
                        "CitySelector": 2,
                        "LocalExpert": 3,
                        "FlightFinder": 4,
                        "AccommodationFinder": 5,
                        "LocalTravelAdvisor": 6,
                        "ItineraryPlanner": 7,
                    }
                    agent_idx = agent_order.get(agent_name, 0)
                    if agent_status == "running":
                        pct = int((agent_idx - 1) / 7 * 100)
                        progress_bar.progress(min(pct, 95))
                        status_text.info(f"🔄 **{agent_name}**: {message}")
                    elif agent_status == "done":
                        pct = int(agent_idx / 7 * 100)
                        progress_bar.progress(min(pct, 95))
                        status_text.success(f"✅ **{agent_name}**: {message}")
                    elif agent_status == "skipped":
                        status_text.info(f"⏭️ **{agent_name}**: {message}")
                    
                    with log_container:
                        if agent_status == "running":
                            st.write(f"🔄 **{agent_name}**: {message}")
                        elif agent_status == "done":
                            st.write(f"✅ **{agent_name}**: {message}")
                        elif agent_status == "skipped":
                            st.write(f"⏭️ **{agent_name}**: {message}")
                
                # If we got here without a complete event, check status
                st.session_state.current_page = "trip_plan"
                st.rerun()
                
            except requests.exceptions.Timeout:
                st.error("⏰ Planning timed out. Please try again.")
            except requests.exceptions.ConnectionError:
                st.error("🔌 Could not connect to server. Is the backend running?")
    except Exception as e:
        st.error(f"Error: {str(e)}")

def show_trip_plan():
    """Unified trip view with three main tabs: Flights, Accommodation, Itineraries."""
    if not st.session_state.user:
        st.session_state.current_page = "login"
        st.rerun()
        return

    trip_id = st.session_state.get("current_trip_id")
    if not trip_id:
        st.error("No trip selected")
        return

    st.title("📋 Your Trip Plan")

    try:
        # Get trip details
        trip_response = requests.get(
            f"{API_URL}/trips/{trip_id}",
            params={"user_id": st.session_state.user["id"]}
        )

        if trip_response.status_code != 200:
            st.error("Failed to load trip")
            return

        trip = trip_response.json()
        st.write(f"### {trip['title']}")
        st.write(f"📍 {trip['destination']} | 📅 {trip['start_date']} to {trip['end_date']}")
        st.divider()

        plan_data = trip.get("plan_data", {})
        local_travel_info = plan_data.get("local_travel_info", {})
        local_gems = plan_data.get("local_gems", [])

        # ── Main 3-tab layout ──────────────────────────────────────
        tab_flights, tab_accommodation, tab_itinerary = st.tabs(
            ["✈️ Flights", "🏨 Accommodation", "📅 Itineraries"]
        )

        # ═══════════════════════════════════════════════════════════
        # TAB 1: FLIGHTS
        # ═══════════════════════════════════════════════════════════
        with tab_flights:
            flights_response = requests.get(
                f"{API_URL}/trips/{trip_id}/flights",
                params={"user_id": st.session_state.user["id"]}
            )
            if flights_response.status_code == 200:
                flights = flights_response.json()
                if not flights:
                    st.info("No flights found. Start planning to generate flight options.")
                else:
                    outbound = [f for f in flights if f["flight_type"] == "outbound"]
                    return_flights = [f for f in flights if f["flight_type"] == "return"]

                    for group_label, group_flights in [("🛫 Outbound Flights", outbound), ("🛬 Return Flights", return_flights)]:
                        if not group_flights:
                            continue
                        st.subheader(group_label)

                        # Find currently selected
                        selected_id = None
                        for f in group_flights:
                            if f["status"] in ("selected", "booked"):
                                selected_id = f["id"]
                                break

                        for flight in group_flights:
                            is_selected = flight["id"] == selected_id
                            is_booked = flight["status"] == "booked"

                            border_color = "#27ae60" if is_selected else "#3498db" if is_booked else "#ddd"
                            bg_color = "#f0fdf4" if is_selected else "#f0f7ff" if is_booked else "#fff"

                            with st.container():
                                col_sel, col_info, col_route, col_price = st.columns([1, 3, 4, 2])

                                with col_sel:
                                    if is_booked:
                                        st.success("✓ Booked")
                                    elif is_selected:
                                        st.info("✓ Selected")
                                    else:
                                        if st.button("Select", key=f"sel_fl_{flight['id']}", use_container_width=True):
                                            try:
                                                requests.put(
                                                    f"{API_URL}/trips/{trip_id}/flights/{flight['id']}/select",
                                                    params={"user_id": st.session_state.user["id"]}
                                                )
                                                st.rerun()
                                            except Exception:
                                                st.error("Failed to select flight")

                                with col_info:
                                    st.write(f"**{flight['airline']}**")
                                    st.caption(flight["flight_number"])

                                with col_route:
                                    dep = flight["departure_datetime"][:16].replace("T", " ")
                                    arr = flight["arrival_datetime"][:16].replace("T", " ")
                                    st.write(f"**{flight['from_airport']}** → **{flight['to_airport']}**")
                                    st.caption(f"🛫 {dep}  ·  🛬 {arr}  ·  ⏱️ {flight['duration_minutes'] // 60}h {flight['duration_minutes'] % 60}m")

                                with col_price:
                                    st.write(f"**${flight['price']:.0f}**")
                                    if not is_booked and is_selected:
                                        if st.button("Book", key=f"book_fl_{flight['id']}", use_container_width=True):
                                            try:
                                                resp = requests.post(
                                                    f"{API_URL}/trips/{trip_id}/flights/{flight['id']}/book",
                                                    params={"user_id": st.session_state.user["id"]}
                                                )
                                                if resp.status_code == 200:
                                                    data = resp.json()
                                                    st.success("Booked!")
                                                    st.markdown(f"[Book on airline site]({data['booking_url']})")
                                                    st.rerun()
                                            except Exception:
                                                pass

                                st.divider()
            else:
                st.error("Failed to load flights")

        # ═══════════════════════════════════════════════════════════
        # TAB 2: ACCOMMODATION
        # ═══════════════════════════════════════════════════════════
        with tab_accommodation:
            accs_response = requests.get(
                f"{API_URL}/trips/{trip_id}/accommodations",
                params={"user_id": st.session_state.user["id"]}
            )
            if accs_response.status_code == 200:
                accs = accs_response.json()
                if not accs:
                    st.info("No accommodations found. Start planning to generate options.")
                else:
                    # Group by city
                    cities_seen: list[str] = []
                    accs_by_city: dict[str, list] = {}
                    for a in accs:
                        city = a.get("city", "Unknown")
                        if city not in accs_by_city:
                            cities_seen.append(city)
                            accs_by_city[city] = []
                        accs_by_city[city].append(a)

                    for city in cities_seen:
                        city_accs = accs_by_city[city]
                        st.subheader(f"🏙️ {city}")

                        # Find currently selected
                        selected_id = None
                        for a in city_accs:
                            if a["status"] in ("selected", "booked"):
                                selected_id = a["id"]
                                break

                        for acc in city_accs:
                            is_selected = acc["id"] == selected_id
                            is_booked = acc["status"] == "booked"

                            with st.container():
                                col_sel, col_name, col_details, col_price = st.columns([1, 3, 4, 2])

                                with col_sel:
                                    if is_booked:
                                        st.success("✓ Booked")
                                    elif is_selected:
                                        st.info("✓ Selected")
                                    else:
                                        if st.button("Select", key=f"sel_acc_{acc['id']}", use_container_width=True):
                                            try:
                                                requests.put(
                                                    f"{API_URL}/trips/{trip_id}/accommodations/{acc['id']}/select",
                                                    params={"user_id": st.session_state.user["id"]}
                                                )
                                                st.rerun()
                                            except Exception:
                                                st.error("Failed to select accommodation")

                                with col_name:
                                    st.write(f"**{acc['name']}**")
                                    if acc.get("rating"):
                                        st.caption(f"⭐ {acc['rating']}/5 · {acc['type']}")
                                    else:
                                        st.caption(acc["type"])

                                with col_details:
                                    st.write(f"📍 {acc['address']}")
                                    st.caption(f"📅 {acc['check_in_date']} → {acc['check_out_date']}")
                                    if acc.get("amenities"):
                                        st.caption(f"✓ {', '.join(acc['amenities'][:4])}")

                                with col_price:
                                    st.write(f"**${acc['price_per_night']:.0f}**/night")
                                    st.caption(f"Total: ${acc['total_price']:.0f}")
                                    if not is_booked and is_selected:
                                        if st.button("Book", key=f"book_acc_{acc['id']}", use_container_width=True):
                                            try:
                                                resp = requests.post(
                                                    f"{API_URL}/trips/{trip_id}/accommodations/{acc['id']}/book",
                                                    params={"user_id": st.session_state.user["id"]}
                                                )
                                                if resp.status_code == 200:
                                                    data = resp.json()
                                                    st.success("Booked!")
                                                    st.markdown(f"[Book on site]({data['booking_url']})")
                                                    st.rerun()
                                            except Exception:
                                                pass

                                st.divider()
            else:
                st.error("Failed to load accommodations")

        # ═══════════════════════════════════════════════════════════
        # TAB 3: ITINERARIES (with sub-tabs for travel info & gems)
        # ═══════════════════════════════════════════════════════════
        with tab_itinerary:
            # ── Regenerate button ─────────────────────────────────
            regen_col1, regen_col2 = st.columns([6, 2])
            with regen_col2:
                if st.button("🔄 Regenerate Itinerary", use_container_width=True,
                             help="Re-plan the itinerary based on your selected flights & accommodation. "
                                  "Uses cached destination info — much faster than a full re-plan."):
                    with st.spinner("Regenerating itinerary with selected options…"):
                        try:
                            regen_resp = requests.post(
                                f"{API_URL}/trips/{trip_id}/regenerate-itinerary",
                                params={"user_id": st.session_state.user["id"]},
                                timeout=300,
                            )
                            if regen_resp.status_code == 200:
                                st.success("✅ Itinerary regenerated!")
                                st.rerun()
                            else:
                                detail = regen_resp.json().get("detail", "Unknown error")
                                st.error(f"Regeneration failed: {detail}")
                        except requests.exceptions.Timeout:
                            st.error("⏰ Regeneration timed out.")
                        except Exception as e:
                            st.error(f"Error: {e}")

            # Sub-tabs inside Itineraries
            if local_travel_info or local_gems:
                sub_itinerary, sub_travel_info, sub_hidden_gems = st.tabs(
                    ["📅 Day-by-Day Itinerary", "🗺️ Local Travel Info", "💎 Hidden Gems"]
                )
            else:
                sub_itinerary = st.container()
                sub_travel_info = None
                sub_hidden_gems = None

            # --- SUB-TAB: Local Travel Info ---
            if sub_travel_info is not None and local_travel_info:
                with sub_travel_info:
                    st.subheader("🗺️ Essential Local Travel Information")
                    st.caption("Practical tips to help you navigate like a local")

                    apps = local_travel_info.get("transport_apps", [])
                    if apps:
                        st.markdown("#### 📱 Apps to Install Before You Go")
                        for app_info in apps:
                            app_type = app_info.get("type", "recommended")
                            if app_type == "essential":
                                badge = "🟢 Essential"
                            elif app_type == "recommended":
                                badge = "🔵 Recommended"
                            else:
                                badge = "⚪ Helpful"
                            st.markdown(
                                f"**{app_info['name']}** &nbsp; `{badge}`\n\n"
                                f"{app_info.get('description', '')}"
                            )
                            st.write("")

                    payment = local_travel_info.get("payment_info", {})
                    if payment:
                        st.markdown("#### 💳 Money & Payment")
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.metric("Currency", payment.get("currency", "N/A"))
                        with col_b:
                            cash_pref = payment.get("cash_preferred", False)
                            st.metric("Cash Preferred?", "Yes" if cash_pref else "No")
                        st.info(payment.get("cards_accepted", ""))
                        if payment.get("tips"):
                            st.success(f"💡 **Tip:** {payment['tips']}")

                    tipping = local_travel_info.get("tipping_customs", "")
                    if tipping:
                        st.markdown("#### 🪙 Tipping Customs")
                        st.write(tipping)

                    lang = local_travel_info.get("language_tips", "")
                    if lang:
                        st.markdown("#### 🗣️ Language Tips")
                        st.write(lang)

                    sim = local_travel_info.get("sim_and_connectivity", "")
                    if sim:
                        st.markdown("#### 📶 SIM Cards & WiFi")
                        st.write(sim)

                    etiquette = local_travel_info.get("local_etiquette", [])
                    if etiquette:
                        st.markdown("#### 🎌 Local Etiquette & Cultural Tips")
                        for rule in etiquette:
                            st.markdown(f"- {rule}")

            # --- SUB-TAB: Hidden Gems ---
            if sub_hidden_gems is not None and local_gems:
                with sub_hidden_gems:
                    st.subheader("💎 Hidden Gems & Local Favorites")
                    st.caption("Authentic places beyond the tourist traps, recommended by locals")

                    categories = {
                        "hidden_gem": ("🔮 Hidden Gems", []),
                        "local_favorite": ("❤️ Local Favorites", []),
                        "authentic_experience": ("🎭 Authentic Experiences", []),
                    }
                    for gem in local_gems:
                        cat = gem.get("category", "hidden_gem")
                        if cat in categories:
                            categories[cat][1].append(gem)
                        else:
                            categories["hidden_gem"][1].append(gem)

                    for cat_key, (cat_label, cat_gems) in categories.items():
                        if not cat_gems:
                            continue
                        st.markdown(f"#### {cat_label}")
                        for gem in cat_gems:
                            with st.container():
                                col1, col2 = st.columns([5, 2])
                                with col1:
                                    st.markdown(f"**{gem['name']}**")
                                    st.write(gem.get("description", ""))
                                    if gem.get("why_special"):
                                        st.info(f"✨ **Why it's special:** {gem['why_special']}")
                                    tags = gem.get("best_for", [])
                                    if tags:
                                        st.caption(" · ".join(f"#{t}" for t in tags))
                                with col2:
                                    nbh = gem.get("neighborhood", "")
                                    city_n = gem.get("city", "")
                                    if nbh:
                                        st.write(f"📍 {nbh}")
                                    if city_n:
                                        st.write(f"🏙️ {city_n}")
                                    maps_url = gem.get("google_maps_url", "")
                                    if maps_url:
                                        st.markdown(f"[🗺️ View on Map]({maps_url})")
                                    source = gem.get("source", "")
                                    if source:
                                        st.caption(f"Source: {source}")
                                st.divider()

            # --- SUB-TAB: Day-by-Day Itinerary ---
            with sub_itinerary:
                response = requests.get(
                    f"{API_URL}/trips/{trip_id}/itinerary",
                    params={"user_id": st.session_state.user["id"]}
                )

                if response.status_code == 200:
                    data = response.json()
                    days = data.get("days", [])

                    if not days:
                        st.info("No itinerary items yet. Start planning first!")
                    else:
                        # ── iCal download ────────────────────────────────
                        ical_bytes = generate_ical(trip, days)
                        safe_name = trip.get("title", "trip").replace(" ", "_")
                        st.download_button(
                            label="📅 Download iCal (.ics)",
                            data=ical_bytes,
                            file_name=f"{safe_name}.ics",
                            mime="text/calendar",
                        )

                        # Day selector
                        day_options = [f"Day {d['day_number']}" for d in days]
                        selected_day = st.selectbox("Select Day", day_options)
                        selected_day_num = int(selected_day.split()[1])

                        day_data = next((d for d in days if d["day_number"] == selected_day_num), None)

                        if day_data:
                            items = day_data["items"]
                            st.subheader(f"Day {selected_day_num} - {len(items)} activities")

                            # ── Map widget ────────────────────────────────
                            destination = data.get("destination", "")
                            map_points = []
                            unmapped = []
                            with st.spinner("Mapping locations…"):
                                for act_idx, itm in enumerate(items, 1):
                                    loc = itm.get("location")
                                    if loc:
                                        coords = geocode_location(loc, destination)
                                        if coords:
                                            map_points.append({
                                                "title": itm["title"],
                                                "location": loc,
                                                "time": itm["start_time"],
                                                "lat": coords[0],
                                                "lon": coords[1],
                                                "num": act_idx,
                                            })
                                        else:
                                            unmapped.append(f"{act_idx}. {itm['title']} ({loc})")

                            if map_points:
                                avg_lat = sum(p["lat"] for p in map_points) / len(map_points)
                                avg_lon = sum(p["lon"] for p in map_points) / len(map_points)

                                m = folium.Map(location=[avg_lat, avg_lon], zoom_start=13, tiles=None)
                                folium.TileLayer(
                                    tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}",
                                    attr="Google",
                                    name="Google Maps",
                                ).add_to(m)

                                for pt in map_points:
                                    num = pt["num"]
                                    folium.Marker(
                                        location=[pt["lat"], pt["lon"]],
                                        popup=folium.Popup(
                                            f"<b>{num}. {pt['title']}</b><br>"
                                            f"🕐 {pt['time']}<br>"
                                            f"📍 {pt['location']}",
                                            max_width=250,
                                        ),
                                        tooltip=f"{num}. {pt['title']}",
                                        icon=folium.DivIcon(
                                            html=(
                                                f'<div style="font-size:14px;color:#fff;'
                                                f'background:#e74c3c;border-radius:50%;'
                                                f'width:28px;height:28px;text-align:center;'
                                                f'line-height:28px;font-weight:bold;'
                                                f'border:2px solid #fff;'
                                                f'box-shadow:0 2px 6px rgba(0,0,0,.3);"'
                                                f'>{num}</div>'
                                            ),
                                            icon_size=(28, 28),
                                            icon_anchor=(14, 14),
                                        ),
                                    ).add_to(m)

                                if len(map_points) > 1:
                                    folium.PolyLine(
                                        locations=[(p["lat"], p["lon"]) for p in map_points],
                                        color="#3498db",
                                        weight=3,
                                        opacity=0.7,
                                        dash_array="10",
                                    ).add_to(m)

                                st_folium(m, height=420, use_container_width=True,
                                          key=f"map_day_{selected_day_num}",
                                          returned_objects=[])

                                if unmapped:
                                    st.warning(
                                        "⚠️ Could not map: " + ", ".join(unmapped)
                                    )
                            else:
                                st.info("📍 No locations could be mapped for this day.")

                            st.divider()

                            # Display items
                            for item in items:
                                with st.container():
                                    col1, col2, col3 = st.columns([2, 6, 2])

                                    with col1:
                                        st.write(f"**{item['start_time']}**")

                                    with col2:
                                        title = item["title"]
                                        if item.get("is_ai_suggested"):
                                            title += " ⭐"
                                        st.write(f"**{title}**")
                                        st.write(f"_{item['description']}_")

                                        if item.get("location"):
                                            maps_url = item.get("google_maps_url", "")
                                            if maps_url:
                                                st.markdown(f"📍 [{item['location']}]({maps_url})")
                                            else:
                                                st.write(f"📍 {item['location']}")

                                        cost_local = item.get("cost_local", "")
                                        cost_usd = item.get("cost_usd", item.get("cost", 0))
                                        currency = item.get("currency", "USD")
                                        if cost_usd and float(cost_usd) > 0:
                                            if currency != "USD" and cost_local:
                                                st.write(f"💵 {cost_local} (~${cost_usd} USD)")
                                            else:
                                                st.write(f"💵 ${cost_usd}")

                                    with col3:
                                        status = item["status"]
                                        if status == "completed":
                                            st.success("✓ Done")
                                        elif status == "delayed":
                                            st.warning("Delayed")
                                        else:
                                            st.info("Planned")

                                        if item["status"] == "planned":
                                            if st.button("✓ Done", key=f"done_{item['id']}"):
                                                try:
                                                    requests.put(
                                                        f"{API_URL}/trips/{trip_id}/itinerary/items/{item['id']}/complete",
                                                        params={"user_id": st.session_state.user["id"]}
                                                    )
                                                    st.rerun()
                                                except Exception:
                                                    pass

                                            new_day = st.number_input(
                                                "Delay to day",
                                                min_value=1,
                                                max_value=len(days),
                                                value=selected_day_num,
                                                key=f"delay_{item['id']}"
                                            )
                                            if st.button("Delay", key=f"delay_btn_{item['id']}"):
                                                try:
                                                    requests.put(
                                                        f"{API_URL}/trips/{trip_id}/itinerary/items/{item['id']}/delay",
                                                        params={"user_id": st.session_state.user["id"], "new_day": new_day}
                                                    )
                                                    st.rerun()
                                                except Exception:
                                                    pass

                                    st.divider()
                else:
                    st.error("Failed to load itinerary")

    except Exception as e:
        st.error(f"Error: {str(e)}")


if __name__ == "__main__":
    main()
