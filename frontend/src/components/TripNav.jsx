import { NavLink, useParams } from 'react-router-dom'
import './TripNav.css'

export default function TripNav() {
  const { tripId } = useParams()

  return (
    <div className="trip-nav">
      <NavLink to={`/trips/${tripId}`} end className="trip-nav__tab">
        📅 Itinerary
      </NavLink>
      <NavLink to={`/trips/${tripId}/flights`} className="trip-nav__tab">
        ✈️ Flights
      </NavLink>
      <NavLink to={`/trips/${tripId}/accommodations`} className="trip-nav__tab">
        🏨 Hotels
      </NavLink>
    </div>
  )
}
