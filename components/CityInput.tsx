import React from 'react'
import { useCityTrigger } from '../hooks/useCityTrigger'

export const CityInput: React.FC = () => {
  const { city, setCity, loading } = useCityTrigger()

  return (
    <div className="space-y-4">
      <div>
        <label htmlFor="city" className="block text-sm font-medium text-gray-700">
          Enter City
        </label>
        <input
          type="text"
          id="city"
          value={city}
          onChange={(e) => setCity(e.target.value)}
          placeholder="Enter city name..."
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
        />
      </div>
      
      {loading && (
        <div className="text-sm text-gray-500">
          Processing {city}...
        </div>
      )}
    </div>
  )
}
