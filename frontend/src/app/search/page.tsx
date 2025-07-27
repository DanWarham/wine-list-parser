'use client'

import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import ClientLayout from '../client-layout'
import { useAuth } from '@/src/supabase-auth-context'
import { api } from '@/utils/api_v2'

export default function SearchPage() {
  const { user, loading, session } = useAuth()
  const router = useRouter()
  const [query, setQuery] = useState('')
  const [filter, setFilter] = useState('')
  const [roleChecked, setRoleChecked] = useState(false)

  useEffect(() => {
    const checkRole = async () => {
      if (!loading && user) {
        try {
          const userInfo = await api.getCurrentUser(session?.access_token ?? '')
          if (userInfo.role === 'admin') {
            router.replace('/admin')
          } else {
            setRoleChecked(true)
          }
        } catch (error) {
          console.error('Role check failed:', error)
          router.replace('/login')
        }
      } else if (!loading && !user) {
        router.replace('/login')
      }
    }
    checkRole()
  }, [user, loading, router, session])

  if (loading || !roleChecked) return <div>Loading...</div>
  if (!user) return null

  return (
    <ClientLayout>
      <div className="container py-8">
        <h1 className="text-2xl font-bold mb-6">Search Wine Lists</h1>
        <div className="flex gap-4 mb-6">
          <input
            type="text"
            placeholder="Search..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="flex-1 rounded-md border px-3 py-2"
          />
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="rounded-md border px-3 py-2"
          >
            <option value="">All</option>
            <option value="red">Red</option>
            <option value="white">White</option>
            <option value="sparkling">Sparkling</option>
          </select>
          <Button>Search</Button>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Search results will go here */}
        </div>
      </div>
    </ClientLayout>
  )
} 