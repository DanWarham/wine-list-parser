import { useState, useCallback } from 'react'
import { Upload, FileText, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { apiPost } from '@/utils/api'
import { cn } from '@/lib/utils'

interface FileUploadProps {
  onFileSelect: (file: File) => void
  accept?: string
  restaurantId: string
}

export default function FileUpload({ onFileSelect, accept = '.pdf,.jpg,.jpeg,.png', restaurantId }: FileUploadProps) {
  const [isDragging, setIsDragging] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleUpload = async (file: File) => {
    setIsUploading(true)
    setError(null)
    
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('restaurant_id', restaurantId)
      
      const response = await apiPost('/auth/wine-lists/upload', formData)
      onFileSelect(file)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
      console.error('Upload failed:', err)
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
          {isUploading ? 'Uploading...' : 'Select File'}
        </Button>
        <input
          id="file-upload"
          type="file"
          className="hidden"
          accept={accept}
          onChange={handleFileInput}
          disabled={isUploading}
        />
        {error && (
          <div className="flex items-center gap-2 text-sm text-destructive">
            <AlertCircle className="h-4 w-4" />
            {error}
          </div>
        )}
      </div>
    </div>
  )
} 