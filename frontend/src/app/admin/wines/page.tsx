'use client'

import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import UserMenu from '@/components/UserMenu'
import { apiGet, apiPut } from '@/utils/api'
import ClientLayout from '../../client-layout'
import { useAuth } from '@/src/supabase-auth-context'

export default function AdminWines() {
  const { user, loading, session } = useAuth()
  const router = useRouter()
  const [wineLists, setWineLists] = useState<any[]>([])
  const [selected, setSelected] = useState('')
  const [entries, setEntries] = useState<any[]>([])
  const [loadingPage, setLoadingPage] = useState(true)
  const [error, setError] = useState('')
  const [editRow, setEditRow] = useState<string | null>(null)
  const [editData, setEditData] = useState<any>({})
  const [roleChecked, setRoleChecked] = useState(false)

  useEffect(() => {
    const checkRole = async () => {
      if (!loading && user) {
        const token = session?.access_token
        const res = await fetch('/api/me', {
          headers: { Authorization: `Bearer ${token}` }
        })
        const userInfo = await res.json()
        if (userInfo.role !== 'admin') {
          router.replace('/search')
        } else {
          setRoleChecked(true)
        }
      } else if (!loading && !user) {
        router.replace('/login')
      }
    }
    checkRole()
  }, [user, loading, router, session])

  useEffect(() => {
    if (roleChecked && user) fetchWineLists()
  }, [roleChecked, user])
  useEffect(() => { if (selected && roleChecked && user) fetchEntries(selected) }, [selected, roleChecked, user])

  async function fetchWineLists() {
    setLoadingPage(true)
    try {
      const res = await apiGet('/wine-lists')
      setWineLists(res.data)
      if (res.data.length) setSelected(res.data[0].id)
    } catch (e) { setError('Failed to load wine lists') }
    setLoadingPage(false)
  }

  async function fetchEntries(fileId: string) {
    setLoadingPage(true)
    try {
      const res = await apiGet(`/wine-entries/${fileId}`)
      setEntries(res.data)
    } catch (e) { setError('Failed to load entries') }
    setLoadingPage(false)
  }

  async function handleEdit(id: string) {
    setEditRow(id)
    const entry = entries.find(e => e.id === id)
    setEditData({ ...entry })
  }

  async function handleSave(id: string) {
    try {
      await apiPut(`/wine-entries/${id}`, editData)
      setEditRow(null)
      fetchEntries(selected)
    } catch (e) { setError('Failed to update') }
  }

  if (loading || !roleChecked || loadingPage) return <div>Loading...</div>
  if (!user) return null

  return (
    <ClientLayout>
      <div>
        <UserMenu />
        <h1>Manage Wine Entries</h1>
        {error && <div style={{ color: 'red' }}>{error}</div>}
        <label>Wine List File: </label>
        <select value={selected} onChange={e => setSelected(e.target.value)}>
          {wineLists.map(wl => <option key={wl.id} value={wl.id}>{wl.filename}</option>)}
        </select>
        <table border={1} cellPadding={6} style={{ width: '100%', marginTop: 16 }}>
          <thead>
            <tr><th>Producer</th><th>Cuvee</th><th>Type</th><th>Vintage</th><th>Price</th><th>Actions</th></tr>
          </thead>
          <tbody>
            {entries.map(e => (
              <tr key={e.id}>
                <td>{editRow === e.id ? <input value={editData.producer || ''} onChange={ev => setEditData((d: any) => ({ ...d, producer: ev.target.value }))} /> : e.producer}</td>
                <td>{editRow === e.id ? <input value={editData.cuvee || ''} onChange={ev => setEditData((d: any) => ({ ...d, cuvee: ev.target.value }))} /> : e.cuvee}</td>
                <td>{editRow === e.id ? <input value={editData.type || ''} onChange={ev => setEditData((d: any) => ({ ...d, type: ev.target.value }))} /> : e.type}</td>
                <td>{editRow === e.id ? <input value={editData.vintage || ''} onChange={ev => setEditData((d: any) => ({ ...d, vintage: ev.target.value }))} /> : e.vintage}</td>
                <td>{editRow === e.id ? <input value={editData.price || ''} onChange={ev => setEditData((d: any) => ({ ...d, price: ev.target.value }))} /> : e.price}</td>
                <td>
                  {editRow === e.id ? (
                    <>
                      <button onClick={() => handleSave(e.id)}>Save</button>
                      <button onClick={() => setEditRow(null)}>Cancel</button>
                    </>
                  ) : (
                    <button onClick={() => handleEdit(e.id)}>Edit</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </ClientLayout>
  )
} 