'use client'

import { useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import { useEffect, useState, useCallback } from 'react'
import UserMenu from '@/components/UserMenu'
import { apiGet, apiDelete } from '@/utils/api'
import { useDropzone } from 'react-dropzone'
import { Button } from '@/components/ui/button'
import { Select } from '@/components/ui/select'
import axios from 'axios'
import ClientLayout from '../../client-layout'

interface Restaurant {
  id: string;
  name: string;
}

interface WineList {
  id: string;
  filename: string;
  status: string;
  uploaded_at: string;
}

export default function AdminWineLists() {
  const { data: session, status } = useSession()
  const router = useRouter()
  const [restaurants, setRestaurants] = useState<Restaurant[]>([])
  const [selected, setSelected] = useState('')
  const [wineLists, setWineLists] = useState<WineList[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadError, setUploadError] = useState('')
  const [parsedDate, setParsedDate] = useState('')

  useEffect(() => {
    if (status === 'unauthenticated') router.push('/login')
    else if (status === 'authenticated' && (session?.user as any)?.role !== 'admin') router.push('/search')
  }, [status, session, router])

  useEffect(() => { fetchRestaurants() }, [])
  useEffect(() => { if (selected) fetchWineLists(selected) }, [selected])

  async function fetchRestaurants() {
    setLoading(true)
    try {
      const res = await apiGet('/restaurants')
      setRestaurants(res.data)
      if (res.data.length) setSelected(res.data[0].id)
    } catch (e) { setError('Failed to load restaurants') }
    setLoading(false)
  }

  async function fetchWineLists(restaurantId: string) {
    setLoading(true)
    try {
      const res = await apiGet(`/restaurants/${restaurantId}/wine-lists`)
      setWineLists(res.data)
    } catch (e) { setError('Failed to load wine lists') }
    setLoading(false)
  }

  async function handleDelete(id: string) {
    if (!window.confirm('Delete this wine list file?')) return
    try {
      await apiDelete(`/wine-lists/${id}`)
      fetchWineLists(selected)
    } catch (e) { setError('Failed to delete') }
  }

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (!selected) {
      setUploadError('Please select a restaurant first.')
      return
    }
    if (!acceptedFiles.length) return
    setUploadError('')
    setUploading(true)
    setUploadProgress(0)
    const file = acceptedFiles[0]
    const formData = new FormData()
    formData.append('file', file)
    formData.append('restaurant_id', selected)
    if (parsedDate) formData.append('parsed_date', parsedDate)
    try {
      const sessionToken = (session as any)?.accessToken
      await axios.post(
        'http://127.0.0.1:8000/api/wine-lists/upload',
        formData,
        {
          headers: {
            'Authorization': sessionToken ? `Bearer ${sessionToken}` : undefined,
            'Content-Type': 'multipart/form-data'
          },
          onUploadProgress: (progressEvent: any) => {
            if (progressEvent.total) {
              setUploadProgress(Math.round((progressEvent.loaded * 100) / progressEvent.total))
            }
          }
        }
      )
      setUploading(false)
      setUploadProgress(0)
      setParsedDate('')
      fetchWineLists(selected)
    } catch (e: any) {
      setUploading(false)
      setUploadError('Upload failed. ' + (e.response?.data?.detail || e.message))
    }
  }, [selected, session, parsedDate])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    multiple: false
  })

  if (status === 'loading' || loading) return <div>Loading...</div>

  return (
    <ClientLayout>
      <div className="container py-6">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold">Manage Wine List Files</h1>
          <UserMenu />
        </div>
        
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

          <div className="rounded-lg border p-6">
            <div
              {...getRootProps()}
              className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                isDragActive ? 'border-primary bg-primary/5' : 'border-muted-foreground/25 hover:border-primary/50'
              }`}
            >
              <input {...getInputProps()} />
              {isDragActive ? (
                <p className="text-lg">Drop the PDF here ...</p>
              ) : (
                <p className="text-lg">Drag & drop a PDF wine list here, or click to select file</p>
              )}
            </div>
            
            <div className="mt-4">
              <input
                type="date"
                value={parsedDate}
                onChange={(e) => setParsedDate(e.target.value)}
                className="w-full rounded-md border px-3 py-2 text-sm"
                placeholder="Parsed Date (optional)"
              />
            </div>
            
            {uploading && (
              <div className="mt-4">
                <div className="h-2 bg-muted rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary transition-all duration-300"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
                <p className="text-sm text-muted-foreground mt-2">Uploading... {uploadProgress}%</p>
              </div>
            )}
            
            {uploadError && (
              <div className="mt-4 text-destructive text-sm">{uploadError}</div>
            )}
          </div>

          <div className="rounded-lg border">
            <table className="w-full">
              <thead className="bg-muted/50">
                <tr>
                  <th className="p-4 text-left font-medium">Filename</th>
                  <th className="p-4 text-left font-medium">Status</th>
                  <th className="p-4 text-left font-medium">Uploaded</th>
                  <th className="p-4 text-left font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {wineLists.map(wl => (
                  <tr key={wl.id} className="border-t">
                    <td className="p-4">{wl.filename}</td>
                    <td className="p-4">{wl.status}</td>
                    <td className="p-4">{wl.uploaded_at}</td>
                    <td className="p-4">
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => handleDelete(wl.id)}
                      >
                        Delete
                      </Button>
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