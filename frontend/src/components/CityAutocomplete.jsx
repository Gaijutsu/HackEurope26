import { useState, useRef, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { searchCities } from '../data/cities'
import './CityAutocomplete.css'

export default function CityAutocomplete({ value, onChange, onValidSelect, disabled, className = 'landing__input', placeholder = 'Where do you want to go?' }) {
    const [suggestions, setSuggestions] = useState([])
    const [isOpen, setIsOpen] = useState(false)
    const [isLoading, setIsLoading] = useState(false)
    const [activeIndex, setActiveIndex] = useState(-1)
    const wrapperRef = useRef(null)
    const inputRef = useRef(null)
    const listRef = useRef(null)
    const debounceRef = useRef(null)

    // Debounced search — waits 250ms after last keystroke
    const debouncedSearch = useCallback(async (query) => {
        if (debounceRef.current) clearTimeout(debounceRef.current)

        if (!query || query.trim().length < 2) {
            setSuggestions([])
            setIsOpen(false)
            setIsLoading(false)
            return
        }

        setIsLoading(true)

        debounceRef.current = setTimeout(async () => {
            const results = await searchCities(query)
            setSuggestions(results)
            setIsOpen(results.length > 0)
            setIsLoading(false)
            setActiveIndex(-1)
        }, 250)
    }, [])

    // Cleanup debounce on unmount
    useEffect(() => {
        return () => {
            if (debounceRef.current) clearTimeout(debounceRef.current)
        }
    }, [])

    // Update suggestions when input changes
    const handleInputChange = useCallback((e) => {
        const val = e.target.value
        onChange(val)
        debouncedSearch(val)
    }, [onChange, debouncedSearch])

    // Select a city from the dropdown
    const selectCity = useCallback((entry) => {
        onChange(entry.city)
        setSuggestions([])
        setIsOpen(false)
        setActiveIndex(-1)
        setIsLoading(false)
        onValidSelect?.(entry)
    }, [onChange, onValidSelect])

    // Keyboard navigation
    const handleKeyDown = useCallback((e) => {
        if (!isOpen || suggestions.length === 0) {
            return
        }

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault()
                setActiveIndex((prev) => (prev < suggestions.length - 1 ? prev + 1 : 0))
                break
            case 'ArrowUp':
                e.preventDefault()
                setActiveIndex((prev) => (prev > 0 ? prev - 1 : suggestions.length - 1))
                break
            case 'Enter':
                e.preventDefault()
                if (activeIndex >= 0 && activeIndex < suggestions.length) {
                    selectCity(suggestions[activeIndex])
                } else if (suggestions.length > 0) {
                    selectCity(suggestions[0])
                }
                break
            case 'Escape':
                setIsOpen(false)
                setActiveIndex(-1)
                break
            default:
                break
        }
    }, [isOpen, suggestions, activeIndex, selectCity])

    // Scroll active item into view
    useEffect(() => {
        if (activeIndex >= 0 && listRef.current) {
            const items = listRef.current.querySelectorAll('.autocomplete__item')
            if (items[activeIndex]) {
                items[activeIndex].scrollIntoView({ block: 'nearest' })
            }
        }
    }, [activeIndex])

    // Close dropdown when clicking outside
    useEffect(() => {
        const handleClickOutside = (e) => {
            if (wrapperRef.current && !wrapperRef.current.contains(e.target)) {
                setIsOpen(false)
                setActiveIndex(-1)
            }
        }
        document.addEventListener('mousedown', handleClickOutside)
        return () => document.removeEventListener('mousedown', handleClickOutside)
    }, [])



    return (
        <div className="autocomplete" ref={wrapperRef}>
            <input
                ref={inputRef}
                id="destination-input"
                type="text"
                className={className}
                placeholder={placeholder}
                value={value}
                onChange={handleInputChange}
                onKeyDown={handleKeyDown}
                onFocus={() => {
                    if (value.trim().length >= 2 && suggestions.length > 0) {
                        setIsOpen(true)
                    }
                }}
                autoComplete="off"
                role="combobox"
                aria-expanded={isOpen}
                aria-haspopup="listbox"
                aria-autocomplete="list"
                aria-controls="city-suggestions"
                aria-activedescendant={activeIndex >= 0 ? `city-option-${activeIndex}` : undefined}
                disabled={disabled}
            />

            {/* Subtle loading indicator */}
            {isLoading && (
                <div className="autocomplete__loading">
                    <span className="autocomplete__loading-dot" />
                    <span className="autocomplete__loading-dot" />
                    <span className="autocomplete__loading-dot" />
                </div>
            )}

            <AnimatePresence>
                {isOpen && suggestions.length > 0 && (
                    <motion.ul
                        className="autocomplete__dropdown"
                        ref={listRef}
                        id="city-suggestions"
                        role="listbox"
                        initial={{ opacity: 0, y: -8, scaleY: 0.95 }}
                        animate={{ opacity: 1, y: 0, scaleY: 1 }}
                        exit={{ opacity: 0, y: -8, scaleY: 0.95 }}
                        transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] }}
                    >
                        {suggestions.map((entry, index) => (
                            <li
                                key={`${entry.city}-${entry.country}-${entry.latitude}`}
                                id={`city-option-${index}`}
                                role="option"
                                aria-selected={index === activeIndex}
                                className={`autocomplete__item ${index === activeIndex ? 'autocomplete__item--active' : ''}`}
                                onMouseEnter={() => setActiveIndex(index)}
                                onMouseDown={(e) => {
                                    e.preventDefault()
                                    selectCity(entry)
                                }}
                            >
                                <div className="autocomplete__item-icon">
                                    <svg
                                        width="16"
                                        height="16"
                                        viewBox="0 0 24 24"
                                        fill="none"
                                        stroke="currentColor"
                                        strokeWidth="1.5"
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                    >
                                        <path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z" />
                                        <circle cx="12" cy="10" r="3" />
                                    </svg>
                                </div>
                                <div className="autocomplete__item-text">
                                    <span className="autocomplete__city">{highlightMatch(entry.city, value)}</span>
                                    <span className="autocomplete__country">
                                        {[entry.region, entry.country].filter(Boolean).join(', ')}
                                    </span>
                                </div>

                            </li>
                        ))}
                    </motion.ul>
                )}
            </AnimatePresence>
        </div>
    )
}

/**
 * Highlight the matching portion of the city name
 */
function highlightMatch(text, query) {
    if (!query) return text
    const idx = text.toLowerCase().indexOf(query.toLowerCase())
    if (idx === -1) return text

    return (
        <>
            {text.slice(0, idx)}
            <mark className="autocomplete__highlight">{text.slice(idx, idx + query.length)}</mark>
            {text.slice(idx + query.length)}
        </>
    )
}
