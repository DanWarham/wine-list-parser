"use client"

import { useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import Link from 'next/link'
import { useEffect } from 'react'
import ClientLayout from './client-layout'
import { Wine, Search, Upload } from 'lucide-react'

export default function Home() {
  const { data: session, status } = useSession()
  const router = useRouter()

  useEffect(() => {
    if (status === 'authenticated') {
      if ((session?.user as any)?.role === 'admin') {
        router.replace('/admin')
      } else {
        router.replace('/search')
      }
    }
  }, [status, session, router])

  if (status === 'loading') return <div>Loading...</div>
  if (status === 'authenticated') return null

  return (
    <ClientLayout>
      <main className="container py-12 flex flex-col items-center justify-center min-h-[80vh]">
        <div className="flex flex-col items-center text-center max-w-3xl mx-auto space-y-8">
          <div className="rounded-full bg-primary/10 p-4">
            <Wine className="h-12 w-12 text-primary" />
          </div>
          <h1 className="text-5xl font-bold tracking-tight">
            Wine List Parser
          </h1>
          <p className="text-xl text-muted-foreground max-w-2xl">
            Welcome to Wine List Parser — the easiest way to extract, refine, and manage wine list data from PDF and image menus. Upload, parse, and search wine lists with AI-powered accuracy.
        </p>
          <div className="flex flex-col sm:flex-row gap-4 pt-4">
            <Button asChild size="lg" className="gap-2">
              <Link href="/login">
                <Wine className="h-5 w-5" />
                Login
              </Link>
            </Button>
            <Button asChild size="lg" variant="outline" className="gap-2">
              <Link href="/register">
                <Upload className="h-5 w-5" />
                Create Account
              </Link>
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mt-16 w-full max-w-5xl">
          <div className="card">
            <div className="rounded-full bg-primary/10 p-3 w-fit mb-4">
              <Search className="h-6 w-6 text-primary" />
            </div>
            <h3 className="text-lg font-semibold mb-2">Smart Search</h3>
            <p className="text-muted-foreground">
              Find wines quickly with our powerful search engine that understands wine terminology and characteristics.
            </p>
          </div>
          <div className="card">
            <div className="rounded-full bg-primary/10 p-3 w-fit mb-4">
              <Upload className="h-6 w-6 text-primary" />
            </div>
            <h3 className="text-lg font-semibold mb-2">Easy Upload</h3>
            <p className="text-muted-foreground">
              Upload PDF menus and images with our drag-and-drop interface. We'll handle the rest.
            </p>
          </div>
          <div className="card">
            <div className="rounded-full bg-primary/10 p-3 w-fit mb-4">
              <Wine className="h-6 w-6 text-primary" />
            </div>
            <h3 className="text-lg font-semibold mb-2">Wine Intelligence</h3>
            <p className="text-muted-foreground">
              AI-powered parsing that understands wine lists and extracts structured data automatically.
            </p>
          </div>
        </div>
      </main>
    </ClientLayout>
  )
}
