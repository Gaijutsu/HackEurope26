/**
 * City search using the Open-Meteo Geocoding API.
 * Free, no API key required, worldwide coverage.
 * https://open-meteo.com/en/docs/geocoding-api
 */

let abortController = null

/**
 * Search cities by query string using the Open-Meteo Geocoding API.
 * Returns results with city, country, region, coordinates, and population.
 * Automatically cancels previous in-flight requests (debounce-friendly).
 */
export async function searchCities(query, maxResults = 6) {
    if (!query || query.trim().length < 2) return []

    // Cancel any previous in-flight request
    if (abortController) {
        abortController.abort()
    }
    abortController = new AbortController()

    try {
        const url = `https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(query.trim())}&count=${maxResults}&language=en&format=json`

        const response = await fetch(url, { signal: abortController.signal })
        if (!response.ok) return []

        const data = await response.json()

        if (!data.results || data.results.length === 0) return []

        return data.results.map((r) => ({
            city: r.name,
            country: r.country || '',
            region: r.admin1 || '', // State/province/region
            latitude: r.latitude,
            longitude: r.longitude,
            population: r.population || 0,
            countryCode: r.country_code || '',
        }))
    } catch (err) {
        // Silently handle aborted requests
        if (err.name === 'AbortError') return []
        console.error('City search error:', err)
        return []
    }
}

/**
 * Check if a given string matches a selected city.
 * Since we now use dynamic search, validation is done by checking
 * if the user has explicitly selected from the dropdown.
 */
export function isValidCity(name, selectedCity) {
    if (!name || !selectedCity) return false
    return name.trim().toLowerCase() === selectedCity.city.toLowerCase()
}
