'use client'

import { useRouter } from 'next/navigation'
import { useEffect, useState, ChangeEvent } from 'react'
import { apiGet, apiPost, apiPut, apiDelete } from '@/utils/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import ClientLayout from '../../client-layout'
import { useAuth } from '@/src/supabase-auth-context'

interface Restaurant {
  id: string;
  name: string;
  wine_list_url?: string;
}

interface RestaurantForm {
  name: string;
  wine_list_url: string;
}

export default function AdminRestaurants() {
  const { user, loading, session } = useAuth()
  const router = useRouter()
  const [restaurants, setRestaurants] = useState<Restaurant[]>([])
  const [loadingPage, setLoadingPage] = useState(true)
  const [error, setError] = useState('')
  const [form, setForm] = useState<RestaurantForm>({ name: '', wine_list_url: '' })
  const [editing, setEditing] = useState<string | null>(null)
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

  async function fetchRestaurants() {
    setLoadingPage(true)
    try {
      const res = await apiGet('/restaurants', session!.access_token)
      setRestaurants(res.data)
    } catch (e) { 
      console.error('Failed to load restaurants:', e)
      setError('Failed to load restaurants') 
    }
    setLoadingPage(false)
  }

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    try {
      await apiPost('/restaurants', form, session!.access_token)
      setForm({ name: '', wine_list_url: '' })
      fetchRestaurants()
    } catch (e) { 
      console.error('Failed to add restaurant:', e)
      setError('Failed to add') 
    }
  }

  async function handleDelete(id: string) {
    if (!window.confirm('Delete this restaurant?')) return
    try {
      await apiDelete(`/restaurants/${id}`, session!.access_token)
      fetchRestaurants()
    } catch (e) { 
      console.error('Failed to delete restaurant:', e)
      setError('Failed to delete') 
    }
  }

  async function handleEdit(id: string) {
    setEditing(id)
    const r = restaurants.find(r => r.id === id)
    if (r) {
      setForm({ name: r.name, wine_list_url: r.wine_list_url || '' })
    }
  }

  async function handleUpdate(e: React.FormEvent) {
    e.preventDefault()
    try {
      await apiPut(`/restaurants/${editing}`, form, session!.access_token)
      setEditing(null)
      setForm({ name: '', wine_list_url: '' })
      fetchRestaurants()
    } catch (e) { 
      console.error('Failed to update restaurant:', e)
      setError('Failed to update') 
    }
  }

  // Show loading state while checking auth and role
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

  // Don't render anything if not authenticated
  if (!user || !session) {
    return null
  }

  return (
    <ClientLayout>
      <div className="container py-6">
        <h1 className="text-3xl font-bold mb-6">Manage Restaurants</h1>
        {error && <div className="text-destructive mb-4">{error}</div>}
        
        <form onSubmit={editing ? handleUpdate : handleAdd} className="space-y-4 mb-8 p-6 bg-card rounded-lg border">
          <div className="grid gap-4 md:grid-cols-2">
            <Input
              placeholder="Name"
              value={form.name}
              onChange={(e: ChangeEvent<HTMLInputElement>) => setForm(f => ({ ...f, name: e.target.value }))}
              required
            />
            <Input
              placeholder="Wine List PDF URL (optional)"
              value={form.wine_list_url}
              onChange={(e: ChangeEvent<HTMLInputElement>) => setForm(f => ({ ...f, wine_list_url: e.target.value }))}
            />
          </div>
          <div className="flex gap-2">
            <Button type="submit" variant="default">
              {editing ? 'Update Restaurant' : 'Add New Restaurant'}
            </Button>
            {editing && (
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setEditing(null)
                  setForm({ name: '', wine_list_url: '' })
                }}
              >
                Cancel
              </Button>
            )}
          </div>
        </form>

        <div className="rounded-lg border">
          <table className="w-full">
            <thead className="bg-muted/50">
              <tr>
                <th className="p-4 text-left font-medium">Name</th>
                <th className="p-4 text-left font-medium">Wine List PDF</th>
                <th className="p-4 text-left font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {restaurants.map(r => (
                <tr key={r.id} className="border-t">
                  <td className="p-4">{r.name}</td>
                  <td className="p-4">
                    {r.wine_list_url ? (
                      <a href={r.wine_list_url} target="_blank" rel="noopener noreferrer" className="text-blue-600 underline">PDF</a>
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </td>
                  <td className="p-4">
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleEdit(r.id)}
                      >
                        Edit
                      </Button>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => handleDelete(r.id)}
                      >
                        Delete
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </ClientLayout>
  )
} 