"use client"

import { useState } from 'react'
import { useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import FileUpload from '@/components/FileUpload'
import RestaurantSelect from '@/components/RestaurantSelect'
import { CheckCircle } from 'lucide-react'
import ClientLayout from '../../client-layout'

export default function AdminUploadPage() {
  const { data: session, status } = useSession()
  const router = useRouter()
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [selectedRestaurantId, setSelectedRestaurantId] = useState<string>('')
  const [uploadSuccess, setUploadSuccess] = useState(false)

  // RBAC: Only allow admins
  if (status === 'loading') return <div>Loading...</div>
  if (status === 'unauthenticated') {
    router.push('/login')
    return null
  }
  if ((session?.user as any)?.role !== 'admin') {
    router.push('/search')
    return null
  }

  const handleFileSelect = (file: File) => {
    setSelectedFile(file)
    setUploadSuccess(true)
  }

  return (
    <ClientLayout>
      <main className="container py-6">
        <h1 className="text-3xl font-bold mb-6">Upload Wine List</h1>
        <div className="grid gap-6">
          <div className="rounded-lg border p-4">
            <h2 className="text-xl font-semibold mb-4">Upload Wine List</h2>
            <p className="text-muted-foreground mb-6">
              Upload a wine list for a restaurant. Supported: PDF, JPG, PNG.
            </p>
            <div className="space-y-6">
              <RestaurantSelect
                onSelect={setSelectedRestaurantId}
                selectedId={selectedRestaurantId}
              />
              {selectedRestaurantId ? (
                <FileUpload
                  onFileSelect={handleFileSelect}
                  restaurantId={selectedRestaurantId}
                />
              ) : (
                <div className="text-sm text-muted-foreground">
                  Please select a restaurant to upload a wine list.
                </div>
              )}
            </div>
            {uploadSuccess && selectedFile && (
              <div className="mt-4 p-4 bg-green-50 rounded-lg flex items-center gap-2">
                <CheckCircle className="text-green-600 w-5 h-5" />
                <span className="text-green-700 text-sm font-medium">
                  Successfully uploaded: {selectedFile.name}
                </span>
              </div>
            )}
          </div>
        </div>
      </main>
    </ClientLayout>
  )
} 