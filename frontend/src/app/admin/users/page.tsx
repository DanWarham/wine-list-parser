'use client'

import { useRouter } from 'next/navigation'
import { useEffect, useState, ChangeEvent } from 'react'
import { apiGet, apiPost, apiPut, apiDelete } from '@/utils/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import ClientLayout from '../../client-layout'
import { useAuth } from '@/src/supabase-auth-context'
import { getAuthHeaders } from '@/utils/api'

interface User {
  id: string;
  email: string;
  name: string;
  role: string;
  restaurant_id: string | null;
}

interface UserForm {
  email: string;
  name: string;
  role: string;
  restaurant_id: string;
}

export default function AdminUsers() {
  const { user, loading, session } = useAuth()
  const router = useRouter()
  const [users, setUsers] = useState<User[]>([])
  const [loadingUsers, setLoadingUsers] = useState(true)
  const [error, setError] = useState('')
  const [form, setForm] = useState<UserForm>({ email: '', name: '', role: 'staff', restaurant_id: '' })
  const [editing, setEditing] = useState<string | null>(null)
  const [userRole, setUserRole] = useState<string | null>(null)

  useEffect(() => {
    if (!loading && session) {
      // Fetch user role from backend
      fetch('/api/me', { headers: getAuthHeaders(session.access_token) })
        .then(res => res.json())
        .then(data => setUserRole(data.role))
        .catch(() => setUserRole(null))
    }
  }, [loading, session])

  useEffect(() => {
    if (!loading && (!user || userRole !== 'admin')) {
      router.push('/login')
    }
  }, [user, loading, userRole, router])

  useEffect(() => {
    if (!loading && user && userRole === 'admin') fetchUsers()
  }, [user, loading, userRole])

  async function fetchUsers() {
    setLoadingUsers(true)
    try {
      const res = await fetch('/api/users', { headers: getAuthHeaders(session?.access_token) })
      const data = await res.json()
      setUsers(data)
    } catch (e) { setError('Failed to load users') }
    setLoadingUsers(false)
  }

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    try {
      const payload = {
        email: form.email,
        name: form.name,
        role: form.role,
        ...(form.restaurant_id ? { restaurant_id: form.restaurant_id } : {})
      };
      await fetch('/api/users', {
        method: 'POST',
        headers: getAuthHeaders(session?.access_token),
        body: JSON.stringify(payload)
      })
      setForm({ email: '', name: '', role: 'staff', restaurant_id: '' })
      fetchUsers()
    } catch (e) { setError('Failed to add') }
  }

  async function handleDelete(id: string) {
    if (!window.confirm('Delete this user?')) return
    try {
      await fetch(`/api/users/${id}`, {
        method: 'DELETE',
        headers: getAuthHeaders(session?.access_token)
      })
      fetchUsers()
    } catch (e) { setError('Failed to delete') }
  }

  async function handleEdit(id: string) {
    setEditing(id)
    const u = users.find(u => u.id === id)
    if (u) {
      setForm({ 
        email: u.email, 
        name: u.name, 
        role: u.role, 
        restaurant_id: u.restaurant_id || '' 
      })
    }
  }

  async function handleUpdate(e: React.FormEvent) {
    e.preventDefault()
    try {
      await fetch(`/api/users/${editing}`, {
        method: 'PUT',
        headers: getAuthHeaders(session?.access_token),
        body: JSON.stringify(form)
      })
      setEditing(null)
      setForm({ email: '', name: '', role: 'staff', restaurant_id: '' })
      fetchUsers()
    } catch (e) { setError('Failed to update') }
  }

  if (loading || loadingUsers) return <div>Loading...</div>

  return (
    <ClientLayout>
      <div className="container py-6">
        <h1 className="text-3xl font-bold mb-6">Manage Users</h1>
        {error && <div className="text-destructive mb-4">{error}</div>}
        
        <form onSubmit={editing ? handleUpdate : handleAdd} className="space-y-4 mb-8 p-6 bg-card rounded-lg border">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <Input
              placeholder="Email"
              type="email"
              value={form.email}
              onChange={(e: ChangeEvent<HTMLInputElement>) => setForm(f => ({ ...f, email: e.target.value }))}
              required
              disabled={!!editing}
            />
            <Input
              placeholder="Name"
              value={form.name}
              onChange={(e: ChangeEvent<HTMLInputElement>) => setForm(f => ({ ...f, name: e.target.value }))}
            />
            <Select
              value={form.role}
              onChange={(e: ChangeEvent<HTMLSelectElement>) => setForm(f => ({ ...f, role: e.target.value }))}
            >
              <option value="admin">Admin</option>
              <option value="restaurant_admin">Restaurant Admin</option>
              <option value="staff">Staff</option>
            </Select>
            <Input
              placeholder="Restaurant ID (optional)"
              value={form.restaurant_id}
              onChange={(e: ChangeEvent<HTMLInputElement>) => setForm(f => ({ ...f, restaurant_id: e.target.value }))}
            />
          </div>
          <div className="flex gap-2">
            <Button type="submit" variant="default">
              {editing ? 'Update User' : 'Add New User'}
            </Button>
            {editing && (
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setEditing(null)
                  setForm({ email: '', name: '', role: 'staff', restaurant_id: '' })
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
                <th className="p-4 text-left font-medium">Email</th>
                <th className="p-4 text-left font-medium">Name</th>
                <th className="p-4 text-left font-medium">Role</th>
                <th className="p-4 text-left font-medium">Restaurant</th>
                <th className="p-4 text-left font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map(u => (
                <tr key={u.id} className="border-t">
                  <td className="p-4">{u.email}</td>
                  <td className="p-4">{u.name}</td>
                  <td className="p-4">{u.role}</td>
                  <td className="p-4">{u.restaurant_id}</td>
                  <td className="p-4">
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleEdit(u.id)}
                      >
                        Edit
                      </Button>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => handleDelete(u.id)}
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