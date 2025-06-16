'use client'

import { useRouter } from 'next/navigation'
import { useEffect, useState, useCallback } from 'react'
import UserMenu from '@/components/UserMenu'
import { apiGet, apiDelete } from '@/utils/api'
import { useDropzone } from 'react-dropzone'
import { Button } from '@/components/ui/button'
import { Select } from '@/components/ui/select'
import axios from 'axios'
import ClientLayout from '../../client-layout'
import { useAuth } from '@/src/supabase-auth-context'
import { Loader2, CheckCircle2, XCircle } from 'lucide-react'
import { useRef } from 'react'

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
  const { user, loading, session } = useAuth()
  const router = useRouter()
  const [restaurants, setRestaurants] = useState<Restaurant[]>([])
  const [selected, setSelected] = useState('')
  const [wineLists, setWineLists] = useState<WineList[]>([])
  const [loadingPage, setLoadingPage] = useState(true)
  const [error, setError] = useState('')
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadError, setUploadError] = useState('')
  const [parsedDate, setParsedDate] = useState('')
  const [roleChecked, setRoleChecked] = useState(false)
  const [uploadStatus, setUploadStatus] = useState<'idle'|'uploading'|'processing'|'parsing'|'complete'|'error'>('idle')
  const pollRef = useRef<NodeJS.Timeout|null>(null)

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
      fetchWineLists(selected)
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

  async function fetchWineLists(restaurantId: string) {
    setLoadingPage(true)
    try {
      const res = await apiGet(`/restaurants/${restaurantId}/wine-lists`, session!.access_token)
      setWineLists(res.data)
    } catch (e) { 
      console.error('Failed to load wine lists:', e)
      setError('Failed to load wine lists') 
    }
    setLoadingPage(false)
  }

  async function handleDelete(id: string) {
    if (!window.confirm('Delete this wine list file?')) return
    try {
      await apiDelete(`/wine-lists/${id}`, session!.access_token)
      fetchWineLists(selected)
    } catch (e) { 
      console.error('Failed to delete wine list:', e)
      setError('Failed to delete') 
    }
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
    setUploadStatus('uploading')
    const file = acceptedFiles[0]
    const formData = new FormData()
    formData.append('file', file)
    formData.append('restaurant_id', selected)
    if (parsedDate) formData.append('parsed_date', parsedDate)

    try {
      const response = await axios.post('/api/wine-lists', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
          'Authorization': `Bearer ${session!.access_token}`
        },
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total!)
          setUploadProgress(percentCompleted)
        }
      })
      setUploadStatus('processing')
      // Start polling for status
      pollRef.current = setInterval(async () => {
        try {
          const statusRes = await fetch(`/api/wine-lists/${response.data.id}/status`, {
            headers: { Authorization: `Bearer ${session!.access_token}` }
          })
          const status = await statusRes.json()
          if (status.status === 'complete') {
            setUploadStatus('complete')
            if (pollRef.current) clearInterval(pollRef.current)
            fetchWineLists(selected)
          } else if (status.status === 'error') {
            setUploadStatus('error')
            setUploadError(status.error || 'Failed to process wine list')
            if (pollRef.current) clearInterval(pollRef.current)
          }
        } catch (e) {
          console.error('Failed to check status:', e)
          setUploadStatus('error')
          setUploadError('Failed to check status')
          if (pollRef.current) clearInterval(pollRef.current)
        }
      }, 2000)
    } catch (e) {
      console.error('Upload failed:', e)
      setUploadStatus('error')
      setUploadError('Failed to upload file')
    }
    setUploading(false)
  }, [selected, parsedDate, session])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    multiple: false
  })

  if (loading || !roleChecked || loadingPage) return <div>Loading...</div>
  if (!user) return null

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
                <div className="flex items-center gap-2 mt-2">
                  {uploadStatus === 'uploading' && <Loader2 className="animate-spin h-4 w-4 text-primary" />}
                  {uploadStatus === 'processing' && <Loader2 className="animate-spin h-4 w-4 text-primary" />}
                  {uploadStatus === 'parsing' && <Loader2 className="animate-spin h-4 w-4 text-primary" />}
                  {uploadStatus === 'complete' && <CheckCircle2 className="h-4 w-4 text-green-600" />}
                  {uploadStatus === 'error' && <XCircle className="h-4 w-4 text-red-600" />}
                  <p className="text-sm text-muted-foreground">
                    {uploadStatus === 'uploading' && `Uploading... ${uploadProgress}%`}
                    {uploadStatus === 'processing' && 'Processing...'}
                    {uploadStatus === 'parsing' && 'Parsing...'}
                    {uploadStatus === 'complete' && 'Complete!'}
                    {uploadStatus === 'error' && 'Error'}
                  </p>
                  {uploadStatus !== 'uploading' && uploadStatus !== 'complete' && (
                    <Button size="sm" variant="ghost" onClick={() => { if (pollRef.current) clearInterval(pollRef.current); setUploading(false); setUploadStatus('idle'); }}>
                      Cancel
                    </Button>
                  )}
                </div>
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