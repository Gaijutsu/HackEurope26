// Comprehensive list of popular travel destination cities worldwide
// Each entry has the city name, country, and optional region for disambiguation

const CITIES = [
    // Europe
    { city: 'Paris', country: 'France', region: 'Europe' },
    { city: 'London', country: 'United Kingdom', region: 'Europe' },
    { city: 'Rome', country: 'Italy', region: 'Europe' },
    { city: 'Barcelona', country: 'Spain', region: 'Europe' },
    { city: 'Amsterdam', country: 'Netherlands', region: 'Europe' },
    { city: 'Berlin', country: 'Germany', region: 'Europe' },
    { city: 'Prague', country: 'Czech Republic', region: 'Europe' },
    { city: 'Vienna', country: 'Austria', region: 'Europe' },
    { city: 'Lisbon', country: 'Portugal', region: 'Europe' },
    { city: 'Madrid', country: 'Spain', region: 'Europe' },
    { city: 'Dublin', country: 'Ireland', region: 'Europe' },
    { city: 'Edinburgh', country: 'United Kingdom', region: 'Europe' },
    { city: 'Florence', country: 'Italy', region: 'Europe' },
    { city: 'Venice', country: 'Italy', region: 'Europe' },
    { city: 'Milan', country: 'Italy', region: 'Europe' },
    { city: 'Munich', country: 'Germany', region: 'Europe' },
    { city: 'Copenhagen', country: 'Denmark', region: 'Europe' },
    { city: 'Stockholm', country: 'Sweden', region: 'Europe' },
    { city: 'Oslo', country: 'Norway', region: 'Europe' },
    { city: 'Helsinki', country: 'Finland', region: 'Europe' },
    { city: 'Athens', country: 'Greece', region: 'Europe' },
    { city: 'Santorini', country: 'Greece', region: 'Europe' },
    { city: 'Mykonos', country: 'Greece', region: 'Europe' },
    { city: 'Istanbul', country: 'Turkey', region: 'Europe' },
    { city: 'Budapest', country: 'Hungary', region: 'Europe' },
    { city: 'Krakow', country: 'Poland', region: 'Europe' },
    { city: 'Warsaw', country: 'Poland', region: 'Europe' },
    { city: 'Dubrovnik', country: 'Croatia', region: 'Europe' },
    { city: 'Split', country: 'Croatia', region: 'Europe' },
    { city: 'Zurich', country: 'Switzerland', region: 'Europe' },
    { city: 'Geneva', country: 'Switzerland', region: 'Europe' },
    { city: 'Interlaken', country: 'Switzerland', region: 'Europe' },
    { city: 'Brussels', country: 'Belgium', region: 'Europe' },
    { city: 'Porto', country: 'Portugal', region: 'Europe' },
    { city: 'Seville', country: 'Spain', region: 'Europe' },
    { city: 'Valencia', country: 'Spain', region: 'Europe' },
    { city: 'Nice', country: 'France', region: 'Europe' },
    { city: 'Lyon', country: 'France', region: 'Europe' },
    { city: 'Marseille', country: 'France', region: 'Europe' },
    { city: 'Reykjavik', country: 'Iceland', region: 'Europe' },
    { city: 'Tallinn', country: 'Estonia', region: 'Europe' },
    { city: 'Riga', country: 'Latvia', region: 'Europe' },
    { city: 'Vilnius', country: 'Lithuania', region: 'Europe' },
    { city: 'Bucharest', country: 'Romania', region: 'Europe' },
    { city: 'Sofia', country: 'Bulgaria', region: 'Europe' },
    { city: 'Belgrade', country: 'Serbia', region: 'Europe' },
    { city: 'Ljubljana', country: 'Slovenia', region: 'Europe' },
    { city: 'Bratislava', country: 'Slovakia', region: 'Europe' },
    { city: 'Monaco', country: 'Monaco', region: 'Europe' },
    { city: 'Malta', country: 'Malta', region: 'Europe' },

    // Asia
    { city: 'Tokyo', country: 'Japan', region: 'Asia' },
    { city: 'Kyoto', country: 'Japan', region: 'Asia' },
    { city: 'Osaka', country: 'Japan', region: 'Asia' },
    { city: 'Seoul', country: 'South Korea', region: 'Asia' },
    { city: 'Bangkok', country: 'Thailand', region: 'Asia' },
    { city: 'Chiang Mai', country: 'Thailand', region: 'Asia' },
    { city: 'Phuket', country: 'Thailand', region: 'Asia' },
    { city: 'Singapore', country: 'Singapore', region: 'Asia' },
    { city: 'Hong Kong', country: 'China', region: 'Asia' },
    { city: 'Shanghai', country: 'China', region: 'Asia' },
    { city: 'Beijing', country: 'China', region: 'Asia' },
    { city: 'Taipei', country: 'Taiwan', region: 'Asia' },
    { city: 'Hanoi', country: 'Vietnam', region: 'Asia' },
    { city: 'Ho Chi Minh City', country: 'Vietnam', region: 'Asia' },
    { city: 'Bali', country: 'Indonesia', region: 'Asia' },
    { city: 'Jakarta', country: 'Indonesia', region: 'Asia' },
    { city: 'Kuala Lumpur', country: 'Malaysia', region: 'Asia' },
    { city: 'Mumbai', country: 'India', region: 'Asia' },
    { city: 'New Delhi', country: 'India', region: 'Asia' },
    { city: 'Jaipur', country: 'India', region: 'Asia' },
    { city: 'Goa', country: 'India', region: 'Asia' },
    { city: 'Kathmandu', country: 'Nepal', region: 'Asia' },
    { city: 'Colombo', country: 'Sri Lanka', region: 'Asia' },
    { city: 'Manila', country: 'Philippines', region: 'Asia' },
    { city: 'Siem Reap', country: 'Cambodia', region: 'Asia' },
    { city: 'Luang Prabang', country: 'Laos', region: 'Asia' },

    // Middle East
    { city: 'Dubai', country: 'UAE', region: 'Middle East' },
    { city: 'Abu Dhabi', country: 'UAE', region: 'Middle East' },
    { city: 'Doha', country: 'Qatar', region: 'Middle East' },
    { city: 'Muscat', country: 'Oman', region: 'Middle East' },
    { city: 'Amman', country: 'Jordan', region: 'Middle East' },
    { city: 'Tel Aviv', country: 'Israel', region: 'Middle East' },
    { city: 'Jerusalem', country: 'Israel', region: 'Middle East' },
    { city: 'Riyadh', country: 'Saudi Arabia', region: 'Middle East' },

    // North America
    { city: 'New York', country: 'USA', region: 'North America' },
    { city: 'Los Angeles', country: 'USA', region: 'North America' },
    { city: 'San Francisco', country: 'USA', region: 'North America' },
    { city: 'Miami', country: 'USA', region: 'North America' },
    { city: 'Chicago', country: 'USA', region: 'North America' },
    { city: 'Las Vegas', country: 'USA', region: 'North America' },
    { city: 'Honolulu', country: 'USA', region: 'North America' },
    { city: 'Washington D.C.', country: 'USA', region: 'North America' },
    { city: 'Boston', country: 'USA', region: 'North America' },
    { city: 'Seattle', country: 'USA', region: 'North America' },
    { city: 'Austin', country: 'USA', region: 'North America' },
    { city: 'Nashville', country: 'USA', region: 'North America' },
    { city: 'New Orleans', country: 'USA', region: 'North America' },
    { city: 'San Diego', country: 'USA', region: 'North America' },
    { city: 'Portland', country: 'USA', region: 'North America' },
    { city: 'Denver', country: 'USA', region: 'North America' },
    { city: 'Toronto', country: 'Canada', region: 'North America' },
    { city: 'Vancouver', country: 'Canada', region: 'North America' },
    { city: 'Montreal', country: 'Canada', region: 'North America' },
    { city: 'Quebec City', country: 'Canada', region: 'North America' },
    { city: 'Mexico City', country: 'Mexico', region: 'North America' },
    { city: 'Cancún', country: 'Mexico', region: 'North America' },
    { city: 'Tulum', country: 'Mexico', region: 'North America' },
    { city: 'Playa del Carmen', country: 'Mexico', region: 'North America' },

    // Central America & Caribbean
    { city: 'Havana', country: 'Cuba', region: 'Caribbean' },
    { city: 'San Juan', country: 'Puerto Rico', region: 'Caribbean' },
    { city: 'Nassau', country: 'Bahamas', region: 'Caribbean' },
    { city: 'Montego Bay', country: 'Jamaica', region: 'Caribbean' },
    { city: 'Aruba', country: 'Aruba', region: 'Caribbean' },
    { city: 'San José', country: 'Costa Rica', region: 'Central America' },
    { city: 'Panama City', country: 'Panama', region: 'Central America' },

    // South America
    { city: 'Rio de Janeiro', country: 'Brazil', region: 'South America' },
    { city: 'São Paulo', country: 'Brazil', region: 'South America' },
    { city: 'Buenos Aires', country: 'Argentina', region: 'South America' },
    { city: 'Bogotá', country: 'Colombia', region: 'South America' },
    { city: 'Cartagena', country: 'Colombia', region: 'South America' },
    { city: 'Medellín', country: 'Colombia', region: 'South America' },
    { city: 'Lima', country: 'Peru', region: 'South America' },
    { city: 'Cusco', country: 'Peru', region: 'South America' },
    { city: 'Santiago', country: 'Chile', region: 'South America' },
    { city: 'Quito', country: 'Ecuador', region: 'South America' },
    { city: 'Montevideo', country: 'Uruguay', region: 'South America' },

    // Africa
    { city: 'Cape Town', country: 'South Africa', region: 'Africa' },
    { city: 'Johannesburg', country: 'South Africa', region: 'Africa' },
    { city: 'Marrakech', country: 'Morocco', region: 'Africa' },
    { city: 'Cairo', country: 'Egypt', region: 'Africa' },
    { city: 'Nairobi', country: 'Kenya', region: 'Africa' },
    { city: 'Zanzibar', country: 'Tanzania', region: 'Africa' },
    { city: 'Accra', country: 'Ghana', region: 'Africa' },
    { city: 'Lagos', country: 'Nigeria', region: 'Africa' },
    { city: 'Casablanca', country: 'Morocco', region: 'Africa' },
    { city: 'Addis Ababa', country: 'Ethiopia', region: 'Africa' },
    { city: 'Windhoek', country: 'Namibia', region: 'Africa' },
    { city: 'Victoria Falls', country: 'Zimbabwe', region: 'Africa' },

    // Oceania
    { city: 'Sydney', country: 'Australia', region: 'Oceania' },
    { city: 'Melbourne', country: 'Australia', region: 'Oceania' },
    { city: 'Brisbane', country: 'Australia', region: 'Oceania' },
    { city: 'Perth', country: 'Australia', region: 'Oceania' },
    { city: 'Auckland', country: 'New Zealand', region: 'Oceania' },
    { city: 'Queenstown', country: 'New Zealand', region: 'Oceania' },
    { city: 'Fiji', country: 'Fiji', region: 'Oceania' },
    { city: 'Bora Bora', country: 'French Polynesia', region: 'Oceania' },
]

/**
 * Search cities by query string.
 * Matches against city name, country, and region.
 * Returns top N results sorted by relevance (city name match first).
 */
export function searchCities(query, maxResults = 6) {
    if (!query || !query.trim()) return []

    const q = query.trim().toLowerCase()

    const scored = CITIES.map((entry) => {
        const cityLower = entry.city.toLowerCase()
        const countryLower = entry.country.toLowerCase()

        let score = 0

        // Exact match
        if (cityLower === q) score = 100
        // Starts with query
        else if (cityLower.startsWith(q)) score = 80
        // Word in city starts with query (e.g. "york" matches "New York")
        else if (cityLower.split(' ').some((w) => w.startsWith(q))) score = 60
        // City contains query
        else if (cityLower.includes(q)) score = 40
        // Country starts with query
        else if (countryLower.startsWith(q)) score = 20
        // Country contains query
        else if (countryLower.includes(q)) score = 10

        return { ...entry, score }
    })
        .filter((entry) => entry.score > 0)
        .sort((a, b) => b.score - a.score)
        .slice(0, maxResults)

    return scored
}

/**
 * Check if a given string exactly matches a city in the database.
 */
export function isValidCity(name) {
    if (!name) return false
    const q = name.trim().toLowerCase()
    return CITIES.some((entry) => entry.city.toLowerCase() === q)
}

export default CITIES
