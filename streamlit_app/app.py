"""
Streamlit Main App - Entry point with navigation
"""
import streamlit as st
import requests
import json

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
    elif st.session_state.current_page == "itinerary":
        show_itinerary()
    elif st.session_state.current_page == "flights":
        show_flights()
    elif st.session_state.current_page == "accommodations":
        show_accommodations()

def show_login():
    st.title("Welcome to Agentic Trip Planner 🤖✈️")
    
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
                            st.error("Invalid email or password")
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
                            st.error("Email already registered")
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
                                    st.session_state.current_page = "itinerary"
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
    
    st.title("🤖 AI is Planning Your Trip...")
    
    # Get trip details
    try:
        trip_response = requests.get(
            f"{API_URL}/trips/{trip_id}",
            params={"user_id": st.session_state.user["id"]}
        )
        
        if trip_response.status_code == 200:
            trip = trip_response.json()
            
            st.write(f"### {trip['title']}")
            st.write(f"📍 {trip['destination']} | 📅 {trip['start_date']} to {trip['end_date']}")
            
            # Check planning status
            status_response = requests.get(
                f"{API_URL}/trips/{trip_id}/plan/status",
                params={"user_id": st.session_state.user["id"]}
            )
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                status = status_data["planning_status"]
                
                if status == "pending":
                    # Start planning
                    with st.spinner("Starting AI planning..."):
                        plan_response = requests.post(
                            f"{API_URL}/trips/{trip_id}/plan",
                            params={"user_id": st.session_state.user["id"]}
                        )
                        
                        if plan_response.status_code == 200:
                            st.success("Planning completed!")
                            st.session_state.current_page = "itinerary"
                            st.rerun()
                        else:
                            st.error("Planning failed. Please try again.")
                
                elif status == "in_progress":
                    st.info("🔄 AI is working on your plan...")
                    st.progress(50)
                    st.write("- Researching destinations...")
                    st.write("- Finding best flights...")
                    st.write("- Curating accommodations...")
                    st.write("- Building your itinerary...")
                    
                    # Auto-refresh
                    st.button("🔄 Check Status", on_click=lambda: None)
                
                elif status == "completed":
                    st.success("✅ Planning completed!")
                    st.balloons()
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("View Itinerary", type="primary", use_container_width=True):
                            st.session_state.current_page = "itinerary"
                            st.rerun()
                    with col2:
                        if st.button("View Flights", use_container_width=True):
                            st.session_state.current_page = "flights"
                            st.rerun()
                
                elif status == "failed":
                    st.error("❌ Planning failed. Please try again.")
                    if st.button("Retry Planning"):
                        plan_response = requests.post(
                            f"{API_URL}/trips/{trip_id}/plan",
                            params={"user_id": st.session_state.user["id"]}
                        )
                        st.rerun()
    except Exception as e:
        st.error(f"Error: {str(e)}")

def show_itinerary():
    if not st.session_state.user:
        st.session_state.current_page = "login"
        st.rerun()
        return
    
    trip_id = st.session_state.get("current_trip_id")
    if not trip_id:
        st.error("No trip selected")
        return
    
    st.title("📅 Your Itinerary")
    
    try:
        # Get trip details
        trip_response = requests.get(
            f"{API_URL}/trips/{trip_id}",
            params={"user_id": st.session_state.user["id"]}
        )
        
        if trip_response.status_code == 200:
            trip = trip_response.json()
            st.write(f"### {trip['title']}")
            st.write(f"📍 {trip['destination']}")
        
        # Get itinerary
        response = requests.get(
            f"{API_URL}/trips/{trip_id}/itinerary",
            params={"user_id": st.session_state.user["id"]}
        )
        
        if response.status_code == 200:
            data = response.json()
            days = data.get("days", [])
            
            if not days:
                st.info("No itinerary items yet. Start planning first!")
                return
            
            # Day selector
            day_options = [f"Day {d['day_number']}" for d in days]
            selected_day = st.selectbox("Select Day", day_options)
            selected_day_num = int(selected_day.split()[1])
            
            # Find selected day data
            day_data = next((d for d in days if d["day_number"] == selected_day_num), None)
            
            if day_data:
                items = day_data["items"]
                
                st.subheader(f"Day {selected_day_num} - {len(items)} activities")
                
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
                                st.write(f"📍 {item['location']}")
                            
                            if item.get("cost", 0) > 0:
                                st.write(f"💵 ${item['cost']}")
                        
                        with col3:
                            # Status
                            status = item["status"]
                            if status == "completed":
                                st.success("✓ Done")
                            elif status == "delayed":
                                st.warning("Delayed")
                            else:
                                st.info("Planned")
                            
                            # Actions
                            if item["status"] == "planned":
                                if st.button("✓ Done", key=f"done_{item['id']}"):
                                    try:
                                        requests.put(
                                            f"{API_URL}/trips/{trip_id}/itinerary/items/{item['id']}/complete",
                                            params={"user_id": st.session_state.user["id"]}
                                        )
                                        st.rerun()
                                    except:
                                        pass
                                
                                # Delay option
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
                                    except:
                                        pass
                        
                        st.divider()
        else:
            st.error("Failed to load itinerary")
    except Exception as e:
        st.error(f"Error: {str(e)}")

def show_flights():
    if not st.session_state.user:
        st.session_state.current_page = "login"
        st.rerun()
        return
    
    trip_id = st.session_state.get("current_trip_id")
    if not trip_id:
        st.error("No trip selected")
        return
    
    st.title("✈️ Flights")
    
    try:
        response = requests.get(
            f"{API_URL}/trips/{trip_id}/flights",
            params={"user_id": st.session_state.user["id"]}
        )
        
        if response.status_code == 200:
            flights = response.json()
            
            if not flights:
                st.info("No flights found. Start planning to generate flight options.")
                return
            
            # Group by type
            outbound = [f for f in flights if f["flight_type"] == "outbound"]
            return_flights = [f for f in flights if f["flight_type"] == "return"]
            
            if outbound:
                st.header("Outbound Flights")
                for flight in outbound:
                    with st.container():
                        col1, col2, col3 = st.columns([3, 5, 2])
                        
                        with col1:
                            st.write(f"**{flight['airline']}**")
                            st.write(f"{flight['flight_number']}")
                        
                        with col2:
                            dep = flight["departure_datetime"][:16].replace("T", " ")
                            arr = flight["arrival_datetime"][:16].replace("T", " ")
                            st.write(f"{flight['from_airport']} → {flight['to_airport']}")
                            st.write(f"🛫 {dep}")
                            st.write(f"🛬 {arr}")
                            st.write(f"⏱️ {flight['duration_minutes'] // 60}h {flight['duration_minutes'] % 60}m")
                        
                        with col3:
                            st.write(f"**${flight['price']}**")
                            
                            if flight["status"] == "booked":
                                st.success("✓ Booked")
                            else:
                                if st.button("Book", key=f"book_{flight['id']}"):
                                    try:
                                        book_response = requests.post(
                                            f"{API_URL}/trips/{trip_id}/flights/{flight['id']}/book",
                                            params={"user_id": st.session_state.user["id"]}
                                        )
                                        if book_response.status_code == 200:
                                            book_data = book_response.json()
                                            st.success("Marked as booked!")
                                            st.markdown(f"[Book on airline site]({book_data['booking_url']})")
                                            st.rerun()
                                    except:
                                        pass
                        
                        st.divider()
            
            if return_flights:
                st.header("Return Flights")
                for flight in return_flights:
                    with st.container():
                        col1, col2, col3 = st.columns([3, 5, 2])
                        
                        with col1:
                            st.write(f"**{flight['airline']}**")
                            st.write(f"{flight['flight_number']}")
                        
                        with col2:
                            dep = flight["departure_datetime"][:16].replace("T", " ")
                            arr = flight["arrival_datetime"][:16].replace("T", " ")
                            st.write(f"{flight['from_airport']} → {flight['to_airport']}")
                            st.write(f"🛫 {dep}")
                            st.write(f"🛬 {arr}")
                            st.write(f"⏱️ {flight['duration_minutes'] // 60}h {flight['duration_minutes'] % 60}m")
                        
                        with col3:
                            st.write(f"**${flight['price']}**")
                            
                            if flight["status"] == "booked":
                                st.success("✓ Booked")
                            else:
                                if st.button("Book", key=f"book_ret_{flight['id']}"):
                                    try:
                                        book_response = requests.post(
                                            f"{API_URL}/trips/{trip_id}/flights/{flight['id']}/book",
                                            params={"user_id": st.session_state.user["id"]}
                                        )
                                        if book_response.status_code == 200:
                                            book_data = book_response.json()
                                            st.success("Marked as booked!")
                                            st.markdown(f"[Book on airline site]({book_data['booking_url']})")
                                            st.rerun()
                                    except:
                                        pass
                        
                        st.divider()
        else:
            st.error("Failed to load flights")
    except Exception as e:
        st.error(f"Error: {str(e)}")

def show_accommodations():
    if not st.session_state.user:
        st.session_state.current_page = "login"
        st.rerun()
        return
    
    trip_id = st.session_state.get("current_trip_id")
    if not trip_id:
        st.error("No trip selected")
        return
    
    st.title("🏨 Accommodations")
    
    try:
        response = requests.get(
            f"{API_URL}/trips/{trip_id}/accommodations",
            params={"user_id": st.session_state.user["id"]}
        )
        
        if response.status_code == 200:
            accs = response.json()
            
            if not accs:
                st.info("No accommodations found. Start planning to generate options.")
                return
            
            for acc in accs:
                with st.container():
                    col1, col2, col3 = st.columns([3, 5, 2])
                    
                    with col1:
                        st.write(f"**{acc['name']}**")
                        st.write(f"⭐ {acc['rating']}/5" if acc['rating'] else "")
                        st.write(f"Type: {acc['type']}")
                    
                    with col2:
                        st.write(f"📍 {acc['city']}")
                        st.write(f"📍 {acc['address']}")
                        st.write(f"📅 {acc['check_in_date']} to {acc['check_out_date']}")
                        
                        if acc['amenities']:
                            st.write(f"✓ {', '.join(acc['amenities'][:3])}")
                    
                    with col3:
                        st.write(f"**${acc['price_per_night']}/night**")
                        st.write(f"Total: ${acc['total_price']}")
                        
                        if acc["status"] == "booked":
                            st.success("✓ Booked")
                        else:
                            if st.button("Book", key=f"book_acc_{acc['id']}"):
                                try:
                                    book_response = requests.post(
                                        f"{API_URL}/trips/{trip_id}/accommodations/{acc['id']}/book",
                                        params={"user_id": st.session_state.user["id"]}
                                    )
                                    if book_response.status_code == 200:
                                        book_data = book_response.json()
                                        st.success("Marked as booked!")
                                        st.markdown(f"[Book on site]({book_data['booking_url']})")
                                        st.rerun()
                                except:
                                    pass
                    
                    st.divider()
        else:
            st.error("Failed to load accommodations")
    except Exception as e:
        st.error(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
