import { useState, useEffect } from 'react'
import { apiGet } from '@/utils/api'

interface Restaurant {
  id: string
  name: string
  contact_email?: string
  notes?: string
}

interface RestaurantSelectProps {
  onSelect: (restaurantId: string) => void
  selectedId?: string
}

export default function RestaurantSelect({ onSelect, selectedId }: RestaurantSelectProps) {
  const [restaurants, setRestaurants] = useState<Restaurant[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchRestaurants = async () => {
      try {
        const response = await apiGet('/auth/restaurants')
        setRestaurants(response.data)
      } catch (err) {
        setError('Failed to load restaurants')
        console.error('Error loading restaurants:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchRestaurants()
  }, [])

  if (loading) {
    return <div className="text-sm text-muted-foreground">Loading restaurants...</div>
  }

  if (error) {
    return <div className="text-sm text-red-600">{error}</div>
  }

  return (
    <div className="space-y-2">
      <label htmlFor="restaurant" className="text-sm font-medium">
        Select Restaurant
      </label>
      <select
        id="restaurant"
        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        value={selectedId || ''}
        onChange={(e) => onSelect(e.target.value)}
      >
        <option value="">Select a restaurant...</option>
        {restaurants.map((restaurant) => (
          <option key={restaurant.id} value={restaurant.id}>
            {restaurant.name}
          </option>
        ))}
      </select>
    </div>
  )
} 