'use client'

import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import ClientLayout from '../client-layout'
import { useAuth } from '@/src/supabase-auth-context'

export default function SearchPage() {
  const { user, loading, session } = useAuth()
  const router = useRouter()
  const [query, setQuery] = useState('')
  const [filter, setFilter] = useState('')
  const [roleChecked, setRoleChecked] = useState(false)

  useEffect(() => {
    const checkRole = async () => {
      if (!loading && user) {
        const token = session?.access_token
        const res = await fetch('/api/me', {
          headers: { Authorization: `Bearer ${token}` }
        })
        const userInfo = await res.json()
        if (userInfo.role === 'admin') {
          router.replace('/admin')
        } else {
          setRoleChecked(true)
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
      <main className="container py-8">
        <h1 className="text-2xl font-bold mb-4">Wine Search</h1>
        <div className="flex flex-col md:flex-row gap-4 mb-6">
          <input
            type="text"
            placeholder="Search wines, producers, regions..."
            className="w-full md:w-1/2 rounded-md border border-input px-3 py-2 text-sm"
            value={query}
            onChange={e => setQuery(e.target.value)}
          />
          <select
            className="w-full md:w-1/4 rounded-md border border-input px-3 py-2 text-sm"
            value={filter}
            onChange={e => setFilter(e.target.value)}
          >
            <option value="">All Restaurants</option>
            {/* TODO: Populate with restaurant list */}
          </select>
          <Button>Search</Button>
        </div>
        <div className="bg-muted rounded-lg p-6 min-h-[200px] flex items-center justify-center text-muted-foreground">
          Search results will appear here.
        </div>
      </main>
    </ClientLayout>
  )
} 