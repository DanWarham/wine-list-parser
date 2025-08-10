'use client'

import { useRouter } from 'next/navigation'
import { useEffect, useState, useCallback, useRef } from 'react'
import UserMenu from '@/components/UserMenu'
import { api } from '@/utils/api_v2'
import { useDropzone } from 'react-dropzone'
import { Button } from '@/components/ui/button'
import ClientLayout from '../../client-layout'
import { useAuth } from '@/src/supabase-auth-context'
import { Loader2, CheckCircle2, XCircle } from 'lucide-react'
import type { Restaurant, WineList } from '@/utils/api_v2'

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
  const [uploadSuccess, setUploadSuccess] = useState('')
  const [parsedDate, setParsedDate] = useState('')
  const [roleChecked, setRoleChecked] = useState(false)
  const [uploadStatus, setUploadStatus] = useState<'idle'|'uploading'|'processing'|'parsing'|'complete'|'error'>('idle')
  const [processingSteps, setProcessingSteps] = useState<any>({})
  const [reprocessingFiles, setReprocessingFiles] = useState<Set<string>>(new Set())
  const pollRef = useRef<NodeJS.Timeout|null>(null)

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

  useEffect(() => {
    if (selected && roleChecked && user && session?.access_token) {
      fetchWineLists(selected)
    }
  }, [selected, roleChecked, user, session])

  async function fetchRestaurants() {
    setLoadingPage(true)
    try {
      const data = await api.getRestaurants(session!.access_token)
      setRestaurants(data)
      if (data.length) setSelected(data[0].id)
    } catch (e) { 
      console.error('Failed to load restaurants:', e)
      setError('Failed to load restaurants') 
    }
    setLoadingPage(false)
  }

  async function fetchWineLists(restaurantId: string) {
    setLoadingPage(true)
    try {
      const data = await api.getWineLists(session!.access_token, restaurantId)
      setWineLists(data)
    } catch (e) { 
      console.error('Failed to load wine lists:', e)
      setError('Failed to load wine lists') 
    }
    setLoadingPage(false)
  }

  async function handleDelete(id: string) {
    if (!window.confirm('Delete this wine list file?')) return
    try {
      await api.deleteWineList(session!.access_token, id)
      fetchWineLists(selected)
    } catch (e) { 
      console.error('Failed to delete wine list:', e)
      setError('Failed to delete') 
    }
  }

  async function handleReprocess(id: string) {
    if (!window.confirm('Reprocess this wine list file?')) return
    try {
      setReprocessingFiles(prev => new Set(prev).add(id))
      await api.reprocessWineList(session!.access_token, id)
      fetchWineLists(selected)
    } catch (e) { 
      console.error('Failed to reprocess wine list:', e)
      setError('Failed to reprocess') 
    } finally {
      setReprocessingFiles(prev => {
        const newSet = new Set(prev)
        newSet.delete(id)
        return newSet
      })
    }
  }

  // Handle status updates from polling
  const handleStatusUpdate = useCallback(async (currentList: any) => {
    // Fetch processing steps for detailed progress
    try {
      const stepsData = await api.getProcessingSteps(session!.access_token, currentList.id)
      setProcessingSteps(stepsData.steps_status || {})
    } catch (error) {
      console.error('Failed to fetch processing steps:', error)
    }
    
    switch (currentList.status) {
      case 'uploaded':
        setUploadStatus('uploading')
        break
      case 'processing':
        setUploadStatus('processing')
        break
      case 'parsed':
        setUploadStatus('complete')
        setUploadSuccess('File processed successfully! Redirecting to results...')
        if (pollRef.current) clearInterval(pollRef.current)
        fetchWineLists(selected)
        // Navigate to refinement page after successful parsing
        setTimeout(() => {
          router.push(`/admin/refine/${currentList.id}`)
        }, 2000) // Small delay to show completion status
        break
      case 'error':
        setUploadStatus('error')
        setUploadError(currentList.notes || 'Failed to process wine list')
        if (pollRef.current) clearInterval(pollRef.current)
        break
      default:
        setUploadStatus(currentList.status as any)
    }
  }, [selected, session, router])

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (!selected) {
      setUploadError('Please select a restaurant first.')
      return
    }
    if (!acceptedFiles.length) return
    setUploadError('')
    setUploadSuccess('')
    setUploading(true)
    setUploadProgress(0)
    setUploadStatus('uploading')
    const file = acceptedFiles[0]
    
    // Log file info for debugging
    console.log(`Uploading file: ${file.name}, Size: ${(file.size / 1024 / 1024).toFixed(2)} MB`)

    try {
      console.log('Starting upload for file:', file.name)
      const wineList = await api.uploadWineList(
        session!.access_token, 
        selected, 
        file,
        (progress) => {
          setUploadProgress(progress);
        }
      )
      
      console.log('Upload API call successful:', wineList)
      setUploadStatus('processing')
      setUploadSuccess('File uploaded successfully! Processing in background...')
      
      // Start polling for status
      pollRef.current = setInterval(async () => {
        try {
          const updatedList = await api.getWineLists(session!.access_token, selected)
          const currentList = updatedList.find(wl => wl.id === wineList.id)
          
          if (currentList) {
            handleStatusUpdate(currentList)
          }
        } catch (e) {
          console.error('Failed to check status:', e)
          // Don't immediately fail - the file might still be processing
          // Only fail after multiple consecutive errors
          if (!pollRef.current) return
          
          // Count consecutive errors
          const errorCount = (pollRef.current as any).errorCount || 0
          ;(pollRef.current as any).errorCount = errorCount + 1
          
          if (errorCount >= 3) {
            setUploadStatus('error')
            setUploadError('Failed to check status after multiple attempts')
            clearInterval(pollRef.current)
          }
        }
      }, 1000) // Poll every second for more responsive updates
    } catch (e: any) {
      console.error('Upload API call failed:', e)
      console.log('Error details:', {
        message: e?.message || 'Unknown error',
        status: e?.response?.status,
        data: e?.response?.data
      })
      
      setUploadStatus('error')
      setUploadError(e?.message || 'Upload failed. Please try again.')
      setUploading(false)
    }
  }, [selected, session])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    multiple: false
  })

  if (loading || !roleChecked || loadingPage) return <div>Loading...</div>
  if (!user) return null

  return (
    <ClientLayout>
      <div className="container py-8">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold">Manage Wine List Files</h1>
          <UserMenu />
        </div>
        
        {error && <div className="text-red-500 mb-4">{error}</div>}
        
        <div className="space-y-6">
          <div className="flex items-center gap-4">
            <label className="text-sm font-medium">Restaurant:</label>
            <select
              value={selected}
              onChange={(e) => setSelected(e.target.value)}
              className="w-[300px] rounded-md border px-3 py-2 text-sm"
            >
              {restaurants.map(r => (
                <option key={r.id} value={r.id}>{r.name}</option>
              ))}
            </select>
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
              <div className="mt-4 space-y-4">
                {/* Upload Progress */}
                <div>
                  <div className="flex justify-between text-xs text-muted-foreground mb-1">
                    <span>Upload Progress</span>
                    <span>{uploadProgress}%</span>
                  </div>
                  <div className="h-2 bg-muted rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary transition-all duration-300"
                      style={{ width: `${uploadProgress}%` }}
                    />
                  </div>
                </div>

                {/* Processing Steps */}
                {Object.keys(processingSteps).length > 0 && (
                  <div className="space-y-2">
                    <h4 className="text-sm font-medium">Processing Steps:</h4>
                    <div className="space-y-2">
                      {Object.entries(processingSteps).map(([step, data]: [string, any]) => (
                        <div key={step} className="flex items-center gap-2 text-sm">
                          {data.status === 'completed' && <CheckCircle2 className="h-4 w-4 text-green-600" />}
                          {data.status === 'in_progress' && <Loader2 className="animate-spin h-4 w-4 text-blue-600" />}
                          {data.status === 'pending' && <div className="h-4 w-4 rounded-full border-2 border-gray-300" />}
                          {data.status === 'error' && <XCircle className="h-4 w-4 text-red-600" />}
                          <span className="capitalize">{step.replace('_', ' ')}:</span>
                          <span className={`text-xs ${
                            data.status === 'completed' ? 'text-green-600' :
                            data.status === 'in_progress' ? 'text-blue-600' :
                            data.status === 'error' ? 'text-red-600' :
                            'text-gray-500'
                          }`}>
                            {data.message}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Status and Actions */}
                <div className="flex items-center gap-2">
                  {uploadStatus === 'uploading' && <Loader2 className="animate-spin h-4 w-4 text-primary" />}
                  {uploadStatus === 'processing' && <Loader2 className="animate-spin h-4 w-4 text-primary" />}
                  {uploadStatus === 'complete' && <CheckCircle2 className="h-4 w-4 text-green-600" />}
                  {uploadStatus === 'error' && <XCircle className="h-4 w-4 text-red-600" />}
                  <p className="text-sm text-muted-foreground">
                    {uploadStatus === 'uploading' && `Uploading file... ${uploadProgress}%`}
                    {uploadStatus === 'processing' && 'Processing wine list with AI in background...'}
                    {uploadStatus === 'complete' && 'Complete! Redirecting to results...'}
                    {uploadStatus === 'error' && 'Error occurred'}
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
            {uploadSuccess && (
              <div className="mt-4 text-green-600 text-sm font-medium">{uploadSuccess}</div>
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
                    <td className="p-4">
                      <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                        wl.status === 'parsed' ? 'bg-green-100 text-green-800' :
                        wl.status === 'processing' ? 'bg-blue-100 text-blue-800' :
                        wl.status === 'uploaded' ? 'bg-yellow-100 text-yellow-800' :
                        wl.status === 'error' ? 'bg-red-100 text-red-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {wl.status === 'parsed' ? '✅ Parsed' :
                         wl.status === 'processing' ? '⏳ Processing' :
                         wl.status === 'uploaded' ? '📤 Uploaded' :
                         wl.status === 'error' ? '❌ Error' :
                         wl.status}
                      </span>
                    </td>
                    <td className="p-4">{wl.uploaded_at}</td>
                    <td className="p-4">
                      <div className="flex gap-2">
                        {wl.status === 'parsed' && (
                          <Button
                            variant="default"
                            size="sm"
                            onClick={() => router.push(`/admin/refine/${wl.id}`)}
                          >
                            View Results
                          </Button>
                        )}
                        {(wl.status === 'error' || wl.status === 'uploaded') && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleReprocess(wl.id)}
                            disabled={reprocessingFiles.has(wl.id)}
                          >
                            {reprocessingFiles.has(wl.id) ? (
                              <>
                                <Loader2 className="animate-spin h-4 w-4 mr-2" />
                                Processing...
                              </>
                            ) : (
                              'Reprocess'
                            )}
                          </Button>
                        )}
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => handleDelete(wl.id)}
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
      </div>
    </ClientLayout>
  )
} 