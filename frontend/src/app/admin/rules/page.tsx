'use client'

import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import { apiGet, apiPut } from '@/utils/api'
import { Button } from '@/components/ui/button'
import { Select } from '@/components/ui/select'
import ClientLayout from '../../client-layout'
import { useAuth } from '@/src/supabase-auth-context'

interface Restaurant {
  id: string;
  name: string;
}

export default function AdminRules() {
  const { user, loading, session } = useAuth()
  const router = useRouter()
  const [restaurants, setRestaurants] = useState<Restaurant[]>([])
  const [selected, setSelected] = useState('')
  const [rules, setRules] = useState('')
  const [loadingPage, setLoadingPage] = useState(true)
  const [error, setError] = useState('')
  const [roleChecked, setRoleChecked] = useState(false)

  useEffect(() => {
    const checkRole = async () => {
      if (loading) return; // Wait for auth to be ready
      
      if (!user || !session) {
        router.push('/login')
        return
      }

      try {
        const token = session.access_token
        const res = await fetch('/api/me', {
          headers: { Authorization: `Bearer ${token}` }
        })
        if (!res.ok) {
          throw new Error('Failed to fetch user info')
        }
        const userInfo = await res.json()
        if (userInfo.role !== 'admin') {
          router.push('/search')
        } else {
          setRoleChecked(true)
        }
      } catch (error) {
        console.error('Role check failed:', error)
        router.push('/login')
      }
    }
    checkRole()
  }, [user, loading, router, session])

  useEffect(() => {
    if (roleChecked && user && session?.access_token) {
      fetchRestaurants()
    }
  }, [roleChecked, user, session])

  useEffect(() => { 
    if (selected && roleChecked && user && session?.access_token) {
      fetchRules(selected)
    }
  }, [selected, roleChecked, user, session])

  async function fetchRestaurants() {
    setLoadingPage(true)
    try {
      const res = await apiGet('/restaurants', session!.access_token)
      setRestaurants(res.data)
      if (res.data.length) setSelected(res.data[0].id)
    } catch (e) { 
      console.error('Failed to load restaurants:', e)
      setError('Failed to load restaurants') 
    }
    setLoadingPage(false)
  }

  async function fetchRules(restaurantId: string) {
    setLoadingPage(true)
    try {
      const res = await apiGet(`/restaurants/${restaurantId}/ruleset`, session!.access_token)
      setRules(JSON.stringify(res.data.rules_json, null, 2))
    } catch (e) { 
      console.error('Failed to load ruleset:', e)
      setError('Failed to load ruleset')
      setRules('') 
    }
    setLoadingPage(false)
  }

  async function handleSave() {
    try {
      await apiPut(`/restaurants/${selected}/ruleset`, { rules_json: JSON.parse(rules) }, session!.access_token)
      alert('Ruleset updated')
    } catch (e) { setError('Failed to update ruleset') }
  }

  if (loading || !roleChecked) {
    return (
      <ClientLayout>
        <div className="container py-8">
          <div className="flex items-center justify-center h-[50vh]">
            <div className="text-lg">Loading...</div>
          </div>
        </div>
      </ClientLayout>
    )
  }

  if (!user || !session) {
    return null
  }

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