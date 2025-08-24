import { useState, useEffect, useCallback } from 'react'

// Simple debounce utility
const debounce = <T extends (...args: any[]) => any>(func: T, delay: number) => {
  let timeoutId: NodeJS.Timeout
  return (...args: Parameters<T>) => {
    clearTimeout(timeoutId)
    timeoutId = setTimeout(() => func.apply(null, args), delay)
  }
}

export const useCityTrigger = () => {
  const [city, setCity] = useState('')
  const [loading, setLoading] = useState(false)
  
  // Debounced function to trigger after user stops typing
  const debouncedTrigger = useCallback(
    debounce(async (cityName: string) => {
      if (!cityName.trim()) return
      
      setLoading(true)
      try {
        // Trigger your webhook or API call
        const response = await fetch('/api/city-trigger', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            city: cityName,
            timestamp: new Date().toISOString(),
            action: 'city_selected'
          })
        })
        
        const result = await response.json()
        console.log('City trigger result:', result)
      } catch (error) {
        console.error('City trigger failed:', error)
      } finally {
        setLoading(false)
      }
    }, 500), // Wait 500ms after user stops typing
    []
  )
  
  useEffect(() => {
    if (city) {
      debouncedTrigger(city)
    }
  }, [city, debouncedTrigger])
  
  return { city, setCity, loading }
}
