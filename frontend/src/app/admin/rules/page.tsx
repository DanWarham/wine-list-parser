'use client'

import { useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import { apiGet, apiPut } from '@/utils/api'
import { Button } from '@/components/ui/button'
import { Select } from '@/components/ui/select'
import ClientLayout from '../../client-layout'

interface Restaurant {
  id: string;
  name: string;
}

export default function AdminRules() {
  const { data: session, status } = useSession()
  const router = useRouter()
  const [restaurants, setRestaurants] = useState<Restaurant[]>([])
  const [selected, setSelected] = useState('')
  const [rules, setRules] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (status === 'unauthenticated') router.push('/login')
    else if (status === 'authenticated' && (session?.user as any)?.role !== 'admin') router.push('/search')
  }, [status, session, router])

  useEffect(() => { fetchRestaurants() }, [])
  useEffect(() => { if (selected) fetchRules(selected) }, [selected])

  async function fetchRestaurants() {
    setLoading(true)
    try {
      const res = await apiGet('/auth/restaurants')
      setRestaurants(res.data)
      if (res.data.length) setSelected(res.data[0].id)
    } catch (e) { setError('Failed to load restaurants') }
    setLoading(false)
  }

  async function fetchRules(restaurantId: string) {
    setLoading(true)
    try {
      const res = await apiGet(`/auth/restaurants/${restaurantId}/ruleset`)
      setRules(JSON.stringify(res.data.rules_json, null, 2))
    } catch (e) { setError('Failed to load ruleset'); setRules('') }
    setLoading(false)
  }

  async function handleSave() {
    try {
      await apiPut(`/auth/restaurants/${selected}/ruleset`, { rules_json: JSON.parse(rules) })
      alert('Ruleset updated')
    } catch (e) { setError('Failed to update ruleset') }
  }

  if (status === 'loading' || loading) return <div>Loading...</div>

  return (
    <ClientLayout>
      <div className="container py-6">
        <h1 className="text-3xl font-bold mb-6">Manage Rules</h1>
        {error && <div className="text-destructive mb-4">{error}</div>}
        
        <div className="space-y-6">
          <div className="flex items-center gap-4">
            <label className="text-sm font-medium">Restaurant:</label>
            <Select
              value={selected}
              onChange={(e) => setSelected(e.target.value)}
              className="w-[300px]"
            >
              {restaurants.map(r => (
                <option key={r.id} value={r.id}>{r.name}</option>
              ))}
            </Select>
          </div>

          <div className="rounded-lg border p-4">
            <textarea
              value={rules}
              onChange={(e) => setRules(e.target.value)}
              className="w-full h-[500px] font-mono text-sm p-4 bg-muted/50 rounded-md focus:outline-none focus:ring-2 focus:ring-ring"
              placeholder="Enter rules in JSON format..."
            />
          </div>

          <Button onClick={handleSave} className="w-full sm:w-auto">
            Save Ruleset
          </Button>
        </div>
      </div>
    </ClientLayout>
  )
} 