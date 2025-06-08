'use client'

import { useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import { useEffect, useState, ChangeEvent } from 'react'
import { apiGet, apiPost, apiPut, apiDelete } from '@/utils/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import ClientLayout from '../../client-layout'

interface User {
  id: string;
  email: string;
  name: string;
  role: string;
  restaurant_id: string | null;
}

interface UserForm {
  email: string;
  password: string;
  name: string;
  role: string;
  restaurant_id: string;
}

export default function AdminUsers() {
  const { data: session, status } = useSession()
  const router = useRouter()
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [form, setForm] = useState<UserForm>({ email: '', password: '', name: '', role: 'staff', restaurant_id: '' })
  const [editing, setEditing] = useState<string | null>(null)

  useEffect(() => {
    if (status === 'unauthenticated') router.push('/login')
    else if (status === 'authenticated' && (session?.user as any)?.role !== 'admin') router.push('/search')
  }, [status, session, router])

  useEffect(() => { fetchUsers() }, [])

  async function fetchUsers() {
    setLoading(true)
    try {
      const res = await apiGet('/auth/users')
      setUsers(res.data)
    } catch (e) { setError('Failed to load users') }
    setLoading(false)
  }

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    try {
      await apiPost('/auth/users', form)
      setForm({ email: '', password: '', name: '', role: 'staff', restaurant_id: '' })
      fetchUsers()
    } catch (e) { setError('Failed to add') }
  }

  async function handleDelete(id: string) {
    if (!window.confirm('Delete this user?')) return
    try {
      await apiDelete(`/auth/users/${id}`)
      fetchUsers()
    } catch (e) { setError('Failed to delete') }
  }

  async function handleEdit(id: string) {
    setEditing(id)
    const u = users.find(u => u.id === id)
    if (u) {
      setForm({ 
        email: u.email, 
        password: '', 
        name: u.name, 
        role: u.role, 
        restaurant_id: u.restaurant_id || '' 
      })
    }
  }

  async function handleUpdate(e: React.FormEvent) {
    e.preventDefault()
    try {
      await apiPut(`/auth/users/${editing}`, form)
      setEditing(null)
      setForm({ email: '', password: '', name: '', role: 'staff', restaurant_id: '' })
      fetchUsers()
    } catch (e) { setError('Failed to update') }
  }

  if (status === 'loading' || loading) return <div>Loading...</div>

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
              placeholder="Password"
              type="password"
              value={form.password}
              onChange={(e: ChangeEvent<HTMLInputElement>) => setForm(f => ({ ...f, password: e.target.value }))}
              required={!editing}
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
                  setForm({ email: '', password: '', name: '', role: 'staff', restaurant_id: '' })
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