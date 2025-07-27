import { useState, useCallback } from 'react'
import { Upload, FileText, AlertCircle, CheckCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { api } from '@/utils/api_v2'
import { cn } from '@/lib/utils'
import { useAuth } from '@/supabase-auth-context'

interface FileUploadProps {
  onFileSelect: (file: File) => void
  accept?: string
  restaurantId: string
}

export default function FileUpload({ onFileSelect, accept = '.pdf,.jpg,.jpeg,.png', restaurantId }: FileUploadProps) {
  const [isDragging, setIsDragging] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const { session } = useAuth()

  const handleUpload = async (file: File) => {
    setIsUploading(true)
    setError(null)
    setSuccess(null)
    
    try {
      if (!session?.access_token) {
        throw new Error('No authentication token available')
      }
      
      console.log('Starting upload for file:', file.name)
      const response = await api.uploadWineList(session.access_token, restaurantId, file)
      console.log('Upload response:', response)
      
      if (response.status === 'parsed') {
        setSuccess(`Successfully processed ${file.name}! ${response.message}`)
        onFileSelect(file)
      } else if (response.status === 'error') {
        throw new Error(response.message || 'Upload failed')
      } else {
        setSuccess(`File uploaded successfully. Status: ${response.status}`)
        onFileSelect(file)
      }
    } catch (err: any) {
      console.error('Upload failed:', err)
      
      // Handle different types of errors
      if (err.name === 'APIError') {
        setError(err.message)
      } else if (err.response?.data?.detail) {
        setError(err.response.data.detail)
      } else if (err.message) {
        setError(err.message)
      } else {
        setError('Upload failed. Please try again.')
      }
    } finally {
      setIsUploading(false)
    }
  }

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    
    const file = e.dataTransfer.files[0]
    if (file) {
      handleUpload(file)
    }
  }, [])

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      handleUpload(file)
    }
  }, [])

  return (
    <div
      className={cn(
        "relative rounded-lg border-2 border-dashed p-8 text-center transition-all",
        isDragging ? "border-primary bg-primary/5" : "border-muted-foreground/25 hover:border-primary/50",
        "bg-card shadow-sm hover:shadow-md"
      )}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <div className="flex flex-col items-center justify-center gap-4">
        <div className="rounded-full bg-primary/10 p-3">
          <Upload className="h-6 w-6 text-primary" />
        </div>
        <div className="space-y-2">
          <h3 className="text-lg font-medium">Upload your wine list</h3>
          <p className="text-sm text-muted-foreground">
            Drag and drop your file here, or click to browse
          </p>
          <p className="text-xs text-muted-foreground">
            Supported formats: PDF, JPG, JPEG, PNG
          </p>
        </div>
        <Button
          variant="outline"
          onClick={() => document.getElementById('file-upload')?.click()}
          disabled={isUploading}
          className="gap-2"
        >
          <FileText className="h-4 w-4" />
          {isUploading ? 'Processing...' : 'Select File'}
        </Button>
        {isUploading && (
          <div className="text-sm text-muted-foreground">
            <p>Uploading and processing your wine list...</p>
            <p className="text-xs">This may take a few moments for large files.</p>
          </div>
        )}
        <input
          id="file-upload"
          type="file"
          className="hidden"
          accept={accept}
          onChange={handleFileInput}
          disabled={isUploading}
        />
        {success && (
          <div className="flex flex-col items-center gap-2 text-sm text-green-600 bg-green-50 p-3 rounded-md border border-green-200">
            <div className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4" />
              <span className="font-medium">Upload Successful</span>
            </div>
            <p className="text-center max-w-md">{success}</p>
          </div>
        )}
        {error && (
          <div className="flex flex-col items-center gap-2 text-sm text-destructive bg-destructive/10 p-3 rounded-md border border-destructive/20">
            <div className="flex items-center gap-2">
              <AlertCircle className="h-4 w-4" />
              <span className="font-medium">Upload Error</span>
            </div>
            <p className="text-center max-w-md">{error}</p>
            <p className="text-xs text-muted-foreground">
              Please check your file format and try again. Supported formats: PDF, JPG, JPEG, PNG
            </p>
          </div>
        )}
      </div>
    </div>
  )
} 