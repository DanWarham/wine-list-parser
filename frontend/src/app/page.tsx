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

  useEffect(() => {
    const checkRoleAndRedirect = async () => {
      if (!loading && user) {
        try {
          const userInfo = await api.getCurrentUser(session?.access_token ?? '')
          if (userInfo.role === 'admin') {
            router.replace('/admin')
          } else {
            router.replace('/search')
          }
        } catch (error) {
          console.error('Role check failed:', error)
          router.replace('/login')
        }
      } else {
        setRoleChecked(true)
      }
    }
    checkRoleAndRedirect()
  }, [user, loading, router, session])

  if (loading || (!user && !roleChecked)) return <div>Loading...</div>
  if (user) return null

  return (
    <ClientLayout>
      <div className="container py-8">
        <div className="text-center">
          <h1 className="text-4xl font-bold mb-4">Welcome to Wine List Parser</h1>
          <p className="text-xl text-muted-foreground mb-8">
            Upload and search through wine lists from your favorite restaurants
          </p>
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
