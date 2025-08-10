'use client'

import { useRouter } from 'next/navigation'
import { useEffect, useState, ChangeEvent } from 'react'
import { api } from '@/utils/api_v2'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import ClientLayout from '../../client-layout'
import { useAuth } from '@/src/supabase-auth-context'
import { Trash2, Settings, Edit } from 'lucide-react'
import type { Restaurant } from '@/utils/api_v2'

interface RestaurantForm {
  name: string;
  address: string; // This will be mapped to wine_list_url in the backend API calls
}

export default function AdminRestaurants() {
  const { user, loading, session } = useAuth()
  const router = useRouter()
  const [restaurants, setRestaurants] = useState<Restaurant[]>([])
  const [loadingPage, setLoadingPage] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [clearingRules, setClearingRules] = useState<Set<string>>(new Set())
  const [form, setForm] = useState<RestaurantForm>({ name: '', address: '' })
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
        const userInfo = await api.getCurrentUser(session.access_token)
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
      const data = await api.getRestaurants(session!.access_token)
      setRestaurants(data)
    } catch (e) { 
      console.error('Failed to load restaurants:', e)
      setError('Failed to load restaurants') 
    }
    setLoadingPage(false)
  }

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setSuccess('')
    try {
      await api.createRestaurant(session!.access_token, {
        name: form.name,
        wine_list_url: form.address
      })
      setForm({ name: '', address: '' })
      fetchRestaurants()
    } catch (e) { 
      console.error('Failed to add restaurant:', e)
      setError('Failed to add') 
    }
  }

  async function handleDelete(id: string, restaurantName: string) {
    const confirmMessage = `Are you sure you want to delete "${restaurantName}"?

This will permanently delete:
• All wine list files uploaded for this restaurant
• All wine entries extracted from those files
• All processing data and analysis results
• All restaurant-specific rules and learning data
• All audit logs related to this restaurant
• All users associated with this restaurant

This action cannot be undone.`

    if (!window.confirm(confirmMessage)) return
    try {
      setError('')
      setSuccess('')
      await api.deleteRestaurant(session!.access_token, id)
      setSuccess(`Restaurant "${restaurantName}" and all associated data deleted successfully`)
      fetchRestaurants()
    } catch (e) { 
      console.error('Failed to delete restaurant:', e)
      setError('Failed to delete restaurant') 
    }
  }

  async function handleEdit(id: string) {
    setEditing(id)
    const r = restaurants.find(r => r.id === id)
    if (r) {
      setForm({ name: r.name, address: r.wine_list_url || '' })
    }
  }

  async function handleUpdate(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setSuccess('')
    try {
      await api.updateRestaurant(session!.access_token, editing!, {
        name: form.name,
        wine_list_url: form.address
      })
      setEditing(null)
      setForm({ name: '', address: '' })
      fetchRestaurants()
    } catch (e) { 
      console.error('Failed to update restaurant:', e)
      setError('Failed to update') 
    }
  }

  async function handleClearRules(id: string, restaurantName: string) {
    if (!window.confirm(`Clear all rules for "${restaurantName}"? This action cannot be undone.`)) return
    try {
      setClearingRules(prev => new Set(prev).add(id))
      await api.clearRestaurantRules(session!.access_token, id)
      setError('') // Clear any previous errors
      setSuccess(`Rules cleared successfully for ${restaurantName}`)
      // Clear success message after 3 seconds
      setTimeout(() => setSuccess(''), 3000)
    } catch (e) { 
      console.error('Failed to clear rules:', e)
      setError('Failed to clear rules') 
    } finally {
      setClearingRules(prev => {
        const newSet = new Set(prev)
        newSet.delete(id)
        return newSet
      })
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
      <div className="container py-8">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold">Manage Restaurants</h1>
        </div>
        
        {error && <div className="text-destructive mb-4">{error}</div>}
        {success && <div className="text-green-600 mb-4 font-medium">{success}</div>}
        
        <div className="space-y-6">
          <div className="rounded-lg border p-6">
            <form onSubmit={editing ? handleUpdate : handleAdd} className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <Input
                  placeholder="Name"
                  value={form.name}
                  onChange={(e: ChangeEvent<HTMLInputElement>) => setForm(f => ({ ...f, name: e.target.value }))}
                  required
                />
                <Input
                  placeholder="Wine List URL (optional)"
                  value={form.address}
                  onChange={(e: ChangeEvent<HTMLInputElement>) => setForm(f => ({ ...f, address: e.target.value }))}
                />
              </div>
              <div className="flex gap-2">
                <Button type="submit">
                  {editing ? 'Update Restaurant' : 'Add New Restaurant'}
                </Button>
                {editing && (
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => {
                      setEditing(null)
                      setForm({ name: '', address: '' })
                    }}
                  >
                    Cancel
                  </Button>
                )}
              </div>
            </form>
          </div>

          <div className="rounded-lg border">
            <table className="w-full">
              <thead className="bg-muted/50">
                <tr>
                  <th className="p-4 text-left font-medium whitespace-nowrap">Name</th>
                  <th className="p-4 text-left font-medium">Wine List URL</th>
                  <th className="p-4 text-left font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {restaurants.map(r => (
                  <tr key={r.id} className="border-t">
                    <td className="p-4 whitespace-nowrap">{r.name}</td>
                    <td className="p-4">
                      {r.wine_list_url ? (
                        <a 
                          href={r.wine_list_url} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:text-blue-800 underline"
                        >
                          {r.wine_list_url}
                        </a>
                      ) : (
                        <span className="text-gray-500">No URL</span>
                      )}
                    </td>
                    <td className="p-4">
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleEdit(r.id)}
                        >
                          <Edit className="h-4 w-4 mr-1" />
                          Edit
                        </Button>
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => handleClearRules(r.id, r.name)}
                          disabled={clearingRules.has(r.id)}
                        >
                          <Settings className="h-4 w-4 mr-1" />
                          {clearingRules.has(r.id) ? 'Clearing...' : 'Clear Rules'}
                        </Button>
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => handleDelete(r.id, r.name)}
                        >
                          <Trash2 className="h-4 w-4 mr-1" />
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
      </div>
    </ClientLayout>
  )
} 