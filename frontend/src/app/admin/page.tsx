'use client'

import { useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import Link from 'next/link'
import ClientLayout from '../client-layout'
import { Wine, Search, Upload, Building2, Users, FileText, Settings } from 'lucide-react'
import { apiGet } from '@/utils/api'

export default function AdminPage() {
  const { data: session, status } = useSession()
  const router = useRouter()
  const [stats, setStats] = useState({
    restaurants: 0,
    users: 0
  })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/login')
    } else if (status === 'authenticated' && (session?.user as any)?.role !== 'admin') {
      router.push('/search')
    }
  }, [status, session, router])

  useEffect(() => {
    async function fetchStats() {
      console.log('Fetching admin stats...');
      try {
        const [restaurantsRes, usersRes] = await Promise.all([
          apiGet('/restaurants'),
          apiGet('/users')
        ])
        console.log('Restaurants API response:', restaurantsRes);
        console.log('Users API response:', usersRes);
        setStats({
          restaurants: Array.isArray(restaurantsRes.data) ? restaurantsRes.data.length : 0,
          users: Array.isArray(usersRes.data) ? usersRes.data.length : 0
        })
      } catch (e) {
        // ignore for now
      }
      setLoading(false)
    }
    fetchStats()
  }, [])

  if (status === 'loading' || loading) return <div>Loading...</div>

  const cards = [
    {
      title: 'Upload Wine List',
      description: 'Upload a new wine list file for a restaurant.',
      icon: <Upload className="h-8 w-8 text-primary" />,
      href: '/admin/upload',
      color: 'bg-red-50'
    },
    {
      title: 'Manage Restaurants',
      description: 'View and edit restaurant information.',
      icon: <Building2 className="h-8 w-8 text-primary" />,
      href: '/admin/restaurants',
      color: 'bg-yellow-50'
    },
    {
      title: 'Manage Wine Lists',
      description: 'View, delete, and manage wine list files.',
      icon: <Wine className="h-8 w-8 text-primary" />,
      href: '/admin/wine-lists',
      color: 'bg-green-50'
    },
    {
      title: 'Manage Users',
      description: 'Add, remove, or update user accounts.',
      icon: <Users className="h-8 w-8 text-primary" />,
      href: '/admin/users',
      color: 'bg-blue-50'
    },
    {
      title: 'Manage Rules',
      description: 'Edit rulesets for wine list parsing.',
      icon: <FileText className="h-8 w-8 text-primary" />,
      href: '/admin/rules',
      color: 'bg-purple-50'
    },
    {
      title: 'Settings',
      description: 'Configure admin and system settings.',
      icon: <Settings className="h-8 w-8 text-primary" />,
      href: '/settings',
      color: 'bg-gray-50'
    }
  ]

  return (
    <ClientLayout>
      <div className="container py-8">
        <h1 className="text-3xl font-bold mb-6">Admin Dashboard</h1>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 mb-8">
          <div className="rounded-lg bg-primary/10 p-6 flex flex-col items-center">
            <Building2 className="h-6 w-6 text-primary mb-2" />
            <div className="text-2xl font-bold">{stats.restaurants}</div>
            <div className="text-sm text-muted-foreground">Restaurants</div>
          </div>
          <div className="rounded-lg bg-primary/10 p-6 flex flex-col items-center">
            <Users className="h-6 w-6 text-primary mb-2" />
            <div className="text-2xl font-bold">{stats.users}</div>
            <div className="text-sm text-muted-foreground">Users</div>
          </div>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {cards.map(card => (
            <div key={card.title} className={`rounded-xl shadow-md p-6 flex flex-col gap-4 ${card.color}`}>
              <div>{card.icon}</div>
              <div className="font-semibold text-lg">{card.title}</div>
              <div className="text-sm text-muted-foreground flex-1">{card.description}</div>
              <Button asChild className="mt-2 w-full">
                <Link href={card.href}>Go to {card.title}</Link>
              </Button>
            </div>
          ))}
        </div>
      </div>
    </ClientLayout>
  )
} 