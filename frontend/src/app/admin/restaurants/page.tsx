'use client'

import { useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import { useEffect, useState, ChangeEvent } from 'react'
import { apiGet, apiPost, apiPut, apiDelete } from '@/utils/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import ClientLayout from '../../client-layout'

interface Restaurant {
  id: string;
  name: string;
  contact_email: string;
  notes: string;
}

interface RestaurantForm {
  name: string;
  contact_email: string;
  notes: string;
}

export default function AdminRestaurants() {
  const { data: session, status } = useSession()
  const router = useRouter()
  const [restaurants, setRestaurants] = useState<Restaurant[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [form, setForm] = useState<RestaurantForm>({ name: '', contact_email: '', notes: '' })
  const [editing, setEditing] = useState<string | null>(null)

  useEffect(() => {
    if (status === 'unauthenticated') router.push('/login')
    else if (status === 'authenticated' && (session?.user as any)?.role !== 'admin') router.push('/search')
  }, [status, session, router])

  useEffect(() => { fetchRestaurants() }, [])

  async function fetchRestaurants() {
    setLoading(true)
    try {
      const res = await apiGet('/restaurants')
      setRestaurants(res.data)
    } catch (e) { setError('Failed to load restaurants') }
    setLoading(false)
  }

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    try {
      await apiPost('/restaurants', form)
      setForm({ name: '', contact_email: '', notes: '' })
      fetchRestaurants()
    } catch (e) { setError('Failed to add') }
  }

  async function handleDelete(id: string) {
    if (!window.confirm('Delete this restaurant?')) return
    try {
      await apiDelete(`/restaurants/${id}`)
      fetchRestaurants()
    } catch (e) { setError('Failed to delete') }
  }

  async function handleEdit(id: string) {
    setEditing(id)
    const r = restaurants.find(r => r.id === id)
    if (r) {
      setForm({ name: r.name, contact_email: r.contact_email, notes: r.notes })
    }
  }

  async function handleUpdate(e: React.FormEvent) {
    e.preventDefault()
    try {
      await apiPut(`/restaurants/${editing}`, form)
      setEditing(null)
      setForm({ name: '', contact_email: '', notes: '' })
      fetchRestaurants()
    } catch (e) { setError('Failed to update') }
  }

  if (status === 'loading' || loading) return <div>Loading...</div>

  return (
    <ClientLayout>
      <div className="container py-6">
        <h1 className="text-3xl font-bold mb-6">Manage Restaurants</h1>
        {error && <div className="text-destructive mb-4">{error}</div>}
        
        <form onSubmit={editing ? handleUpdate : handleAdd} className="space-y-4 mb-8 p-6 bg-card rounded-lg border">
          <div className="grid gap-4 md:grid-cols-3">
            <Input
              placeholder="Name"
              value={form.name}
              onChange={(e: ChangeEvent<HTMLInputElement>) => setForm(f => ({ ...f, name: e.target.value }))}
              required
            />
            <Input
              placeholder="Contact Email"
              type="email"
              value={form.contact_email}
              onChange={(e: ChangeEvent<HTMLInputElement>) => setForm(f => ({ ...f, contact_email: e.target.value }))}
            />
            <Input
              placeholder="Notes"
              value={form.notes}
              onChange={(e: ChangeEvent<HTMLInputElement>) => setForm(f => ({ ...f, notes: e.target.value }))}
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
                  setForm({ name: '', contact_email: '', notes: '' })
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
                <th className="p-4 text-left font-medium">Email</th>
                <th className="p-4 text-left font-medium">Notes</th>
                <th className="p-4 text-left font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {restaurants.map(r => (
                <tr key={r.id} className="border-t">
                  <td className="p-4">{r.name}</td>
                  <td className="p-4">{r.contact_email}</td>
                  <td className="p-4">{r.notes}</td>
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