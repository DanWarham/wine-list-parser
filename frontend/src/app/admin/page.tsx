'use client'

import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import Link from 'next/link'
import ClientLayout from '../client-layout'
import { Wine, Search, Upload, Building2, Users, FileText, Settings } from 'lucide-react'
import { api } from '@/utils/api_v2'
import { useAuth } from '@/src/supabase-auth-context'

export default function AdminPage() {
  const { user, loading, session } = useAuth()
  const router = useRouter()
  const [stats, setStats] = useState({
    restaurants: 0,
    users: 0
  })
  const [loadingStats, setLoadingStats] = useState(true)
  const [roleChecked, setRoleChecked] = useState(false)

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
    if (!loading && user && roleChecked && session?.access_token) {
      const fetchStats = async () => {
        setLoadingStats(true)
        try {
          const [restaurants, users] = await Promise.all([
            api.getRestaurants(session.access_token),
            api.getUsers(session.access_token)
          ])
          setStats({
            restaurants: restaurants.length,
            users: users.length
          })
        } catch (e) {
          console.error('Failed to fetch stats:', e)
        }
        setLoadingStats(false)
      }
      fetchStats()
    }
  }, [user, loading, roleChecked, session])

  // Show loading state while checking auth and role
  if (loading || !roleChecked) {
    return (
      <ClientLayout>
        <div className="container py-8">
          <div className="flex items-center justify-center h-[50vh]">
            <div className="text-lg">Loading...</div>
          </div>
        </div>
      </ClientLayout>
    )
  }

  // Don't render anything if not authenticated
  if (!user || !session) {
    return null
  }

  return (
    <ClientLayout>
      <div className="container py-8">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold">Admin Dashboard</h1>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <Link href="/admin/restaurants" className="block">
            <div className="rounded-lg border bg-card p-6 shadow-sm transition-all hover:shadow-md">
              <div className="flex items-center gap-4">
                <Building2 className="w-8 h-8 text-primary" />
                <div>
                  <h2 className="text-lg font-semibold">Restaurants</h2>
                  <p className="text-2xl font-bold">{stats.restaurants}</p>
                </div>
              </div>
            </div>
          </Link>

          <Link href="/admin/users" className="block">
            <div className="rounded-lg border bg-card p-6 shadow-sm transition-all hover:shadow-md">
              <div className="flex items-center gap-4">
                <Users className="w-8 h-8 text-primary" />
                <div>
                  <h2 className="text-lg font-semibold">Users</h2>
                  <p className="text-2xl font-bold">{stats.users}</p>
                </div>
              </div>
            </div>
          </Link>

          <Link href="/admin/wine-lists" className="block">
            <div className="rounded-lg border bg-card p-6 shadow-sm transition-all hover:shadow-md">
              <div className="flex items-center gap-4">
                <FileText className="w-8 h-8 text-primary" />
                <div>
                  <h2 className="text-lg font-semibold">Wine Lists</h2>
                  <p className="text-2xl font-bold">Manage</p>
                </div>
              </div>
            </div>
          </Link>

          <Link href="/admin/rules" className="block">
            <div className="rounded-lg border bg-card p-6 shadow-sm transition-all hover:shadow-md">
              <div className="flex items-center gap-4">
                <Settings className="w-8 h-8 text-primary" />
                <div>
                  <h2 className="text-lg font-semibold">Rules</h2>
                  <p className="text-2xl font-bold">Configure</p>
                </div>
              </div>
            </div>
          </Link>
        </div>
      </div>
    </ClientLayout>
  )
} 