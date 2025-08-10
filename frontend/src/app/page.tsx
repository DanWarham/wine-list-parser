"use client"

import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import Link from 'next/link'
import { useEffect, useState } from 'react'
import ClientLayout from './client-layout'
import { Wine, Search, Upload } from 'lucide-react'
import { useAuth } from '@/src/supabase-auth-context'
import { api } from '@/utils/api_v2'

export default function Home() {
  const { user, loading, session } = useAuth()
  const router = useRouter()
  const [roleChecked, setRoleChecked] = useState(false)
  const [backendError, setBackendError] = useState(false)

  useEffect(() => {
    const checkRoleAndRedirect = async () => {
      if (!loading && user) {
        try {
          console.log('Checking user role...')
          const userInfo = await api.getCurrentUser(session?.access_token ?? '')
          console.log('User info received:', userInfo)
          if (userInfo.role === 'admin') {
            router.replace('/admin')
          } else {
            router.replace('/search')
          }
        } catch (error: any) {
          console.error('Role check failed:', error)
          // Check if it's a backend connection issue
          if (error.message?.includes('ECONNRESET') || 
              error.message?.includes('socket hang up') ||
              error.message?.includes('Network Error')) {
            setBackendError(true)
            // Don't redirect to login, just show the warning
          } else {
            router.replace('/login')
          }
        }
      } else if (!loading && !user) {
        setRoleChecked(true)
      }
    }
    checkRoleAndRedirect()
  }, [user, loading, router, session])

  if (loading || (!user && !roleChecked)) return <div>Loading...</div>
  if (user && !backendError) return null

  return (
    <ClientLayout>
      <div className="container py-8">
        <div className="text-center">
          <h1 className="text-4xl font-bold mb-4">Welcome to Wine List Parser</h1>
          <p className="text-xl text-muted-foreground mb-8">
            Upload and search through wine lists from your favorite restaurants
          </p>
          
          {backendError && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
              <p className="text-yellow-800 mb-4">
                ⚠️ Backend service is currently unavailable. Some features may not work properly.
              </p>
              {user && (
                <div className="flex flex-col sm:flex-row gap-2 justify-center">
                  <Button asChild size="sm" variant="outline">
                    <Link href="/admin">
                      <Search className="mr-2 h-4 w-4" />
                      Admin Dashboard
                    </Link>
                  </Button>
                  <Button asChild size="sm" variant="outline">
                    <Link href="/search">
                      <Search className="mr-2 h-4 w-4" />
                      Search Wines
                    </Link>
                  </Button>
                </div>
              )}
            </div>
          )}
          
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button asChild size="lg">
              <Link href="/login">
                <Search className="mr-2 h-5 w-5" />
                Get Started
              </Link>
            </Button>
            <Button asChild variant="outline" size="lg">
              <Link href="/register">
                <Upload className="mr-2 h-5 w-5" />
                Create Account
              </Link>
            </Button>
          </div>
        </div>
      </div>
    </ClientLayout>
  )
}
