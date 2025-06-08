'use client'

import { useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import { useEffect } from 'react'
import { Button } from '@/components/ui/button'
import Link from 'next/link'
import ClientLayout from '../client-layout'

export default function AdminPage() {
  const { data: session, status } = useSession()
  const router = useRouter()

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/login')
    } else if (status === 'authenticated' && (session?.user as any)?.role !== 'admin') {
      router.push('/search')
    }
  }, [status, session, router])

  if (status === 'loading') return <div>Loading...</div>

  return (
    <ClientLayout>
      <div>
        <h1>Admin Dashboard</h1>
        <p>Welcome, {session?.user?.name}!</p>
        <p>This is the admin dashboard. (Add admin features here.)</p>
        <div className="mt-8">
          <Button asChild size="lg">
            <Link href="/admin/upload">Upload Wine List</Link>
          </Button>
        </div>
      </div>
    </ClientLayout>
  )
} 