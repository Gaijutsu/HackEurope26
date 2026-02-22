import { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import './ItineraryMap.css'

// Simple in-memory geocoding cache (survives day switches)
const geocodeCache = new Map()

function extractPlaceName(location) {
  // Take the first comma-separated segment (strips neighbourhood/city suffixes)
  let name = location.split(',')[0].trim()
  // "From X to Y" transit patterns — use the destination place
  const toMatch = name.match(/\bto\s+(.+)$/i)
  if (toMatch) name = toMatch[1].trim()
  // Strip parenthetical district tags like "(1er)", "(8e)", "(transfer from ...)"
  name = name.replace(/\s*\([^)]*\)/g, '').trim()
  // Slash-separated alternatives (e.g. "Arc de Triomphe / Champs-Élysées") — keep first
  name = name.split(/\s*\/\s*/)[0].trim()
  return name
}

async function geocodeLocation(location, destination) {
  const cacheKey = `${location}::${destination}`
  if (geocodeCache.has(cacheKey)) return geocodeCache.get(cacheKey)

  const placeName = extractPlaceName(location)
  // Build a deduplicated list of queries from most-specific to least-specific
  const seen = new Set()
  const queries = [
    `${placeName}, ${destination}`,
    `${location}, ${destination}`,
    location,
  ].filter((q) => { if (seen.has(q)) return false; seen.add(q); return true })

  for (const q of queries) {
    try {
      const res = await fetch(
        `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(q)}&format=json&limit=1`,
        { headers: { 'User-Agent': 'precisely-travel-planner/1.0', 'Accept-Language': 'en' } }
      )
      const data = await res.json()
      if (data.length > 0) {
        const result = { lat: parseFloat(data[0].lat), lon: parseFloat(data[0].lon) }
        geocodeCache.set(cacheKey, result)
        return result
      }
    } catch {
      // try next query
    }
  }

  // Don't cache failures — allow retries on next page load
  return null
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

export default function ItineraryMap({ items, destination }) {
  const containerRef = useRef(null)
  const mapRef = useRef(null)
  const layerGroupRef = useRef(null)
  const [mapPoints, setMapPoints] = useState([])
  const [loading, setLoading] = useState(false)

  // Geocode locations whenever items/destination change
  useEffect(() => {
    let cancelled = false

    async function buildPoints() {
      setLoading(true)
      const points = []
      for (const item of items) {
        if (cancelled) break
        if (!item.location) continue
        const coords = await geocodeLocation(item.location, destination)
        if (coords && !cancelled) {
          points.push({ title: item.title, location: item.location, time: item.start_time, ...coords })
        }
        // Respect Nominatim rate limit (1 req/sec)
        await sleep(1100)
      }
      if (!cancelled) {
        setMapPoints(points)
        setLoading(false)
      }
    }

    setMapPoints([])
    if (items.some((it) => it.location)) {
      buildPoints()
    }

    return () => { cancelled = true }
  }, [items, destination])

  // Create the Leaflet map once on mount
  useEffect(() => {
    if (!containerRef.current) return

    const map = L.map(containerRef.current, { zoomControl: true })
    mapRef.current = map

    // Google Maps tiles — same approach as the streamlit/folium implementation
    L.tileLayer('https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}', {
      attribution: 'Map data ©2025 Google',
      maxZoom: 20,
    }).addTo(map)

    // Default view while data loads
    map.setView([48.8566, 2.3522], 12)

    return () => {
      map.remove()
      mapRef.current = null
    }
  }, [])

  // Update markers and route line whenever mapPoints change
  useEffect(() => {
    const map = mapRef.current
    if (!map) return

    // Clear previous markers/polyline
    if (layerGroupRef.current) {
      map.removeLayer(layerGroupRef.current)
    }
    if (mapPoints.length === 0) return

    const group = L.layerGroup()
    layerGroupRef.current = group

    const latlngs = mapPoints.map((p) => [p.lat, p.lon])

    // Numbered markers — mirrors the streamlit DivIcon style
    mapPoints.forEach((pt, idx) => {
      const icon = L.divIcon({
        html: `<div class="itin-map__pin">${idx + 1}</div>`,
        className: '',
        iconSize: [28, 28],
        iconAnchor: [14, 14],
        popupAnchor: [0, -18],
      })
      L.marker([pt.lat, pt.lon], { icon })
        .bindPopup(
          `<div class="itin-map__popup"><strong>${idx + 1}. ${pt.title}</strong><br>🕐 ${pt.time}<br>📍 ${pt.location}</div>`,
          { maxWidth: 260 }
        )
        .addTo(group)
    })

    // Dashed route line — mirrors the streamlit PolyLine
    if (latlngs.length > 1) {
      L.polyline(latlngs, {
        color: '#3498db',
        weight: 3,
        opacity: 0.7,
        dashArray: '10',
      }).addTo(group)
    }

    group.addTo(map)

    if (latlngs.length === 1) {
      map.setView(latlngs[0], 14)
    } else {
      map.fitBounds(latlngs, { padding: [40, 40] })
    }
  }, [mapPoints])

  const showOverlay = loading || mapPoints.length === 0

  return (
    <div className="itin-map">
      {/* Map canvas — always in DOM so Leaflet has correct dimensions */}
      <div ref={containerRef} className="itin-map__canvas" />

      {/* Status overlay */}
      {showOverlay && (
        <div className="itin-map__overlay">
          {loading
            ? <span className="itin-map__spinner">Mapping locations…</span>
            : <span>No mappable locations for this day.</span>
          }
        </div>
      )}
    </div>
  )
}
