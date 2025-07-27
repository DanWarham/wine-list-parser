'use client'
import { cn } from '@/lib/utils'
import { Button } from '../ui/button'
import { Separator } from '../ui/separator'
import Link from 'next/link'
import { 
  Search, 
  Upload, 
  Building2, 
  Wine, 
  Users, 
  Settings, 
  FileText, 
  Download,
  LayoutDashboard
} from 'lucide-react'
import { usePathname } from 'next/navigation'
import { useAuth } from '@/src/supabase-auth-context'
import { useEffect, useState } from 'react'
import { api } from '@/utils/api_v2'

interface SidebarProps extends React.HTMLAttributes<HTMLDivElement> {}

export default function Sidebar({ className, ...props }: SidebarProps) {
  const { user, session } = useAuth()
  const pathname = usePathname()
  const [role, setRole] = useState<string | null>(null)

  useEffect(() => {
    async function fetchRole() {
      if (session?.access_token) {
        try {
          const userInfo = await api.getCurrentUser(session.access_token)
          setRole(userInfo.role)
        } catch {
          setRole(null)
        }
      } else {
        setRole(null)
      }
    }
    fetchRole()
  }, [session?.access_token])

  const isActive = (path: string) => pathname === path

  return (
    <div className={cn("pb-12 w-64", className)} {...props}>
      <div className="space-y-4 py-4">
        <div className="px-3 py-2">
          <h2 className="mb-2 px-4 text-lg font-semibold tracking-tight">
            Navigation
          </h2>
          <div className="space-y-1">
            <Button
              asChild
              variant={isActive('/search') ? 'secondary' : 'ghost'}
              className="w-full justify-start"
            >
              <Link href="/search">
                <Search className="mr-2 h-4 w-4" />
                Search
              </Link>
            </Button>
            {role === 'admin' && (
              <>
                <Button
                  asChild
                  variant={isActive('/admin') ? 'secondary' : 'ghost'}
                  className="w-full justify-start"
                >
                  <Link href="/admin">
                    <LayoutDashboard className="mr-2 h-4 w-4" />
                    Dashboard
                  </Link>
                </Button>
                <Button
                  asChild
                  variant={isActive('/admin/restaurants') ? 'secondary' : 'ghost'}
                  className="w-full justify-start"
                >
                  <Link href="/admin/restaurants">
                    <Building2 className="mr-2 h-4 w-4" />
                    Restaurants
                  </Link>
                </Button>
                <Button
                  asChild
                  variant={isActive('/admin/wine-lists') ? 'secondary' : 'ghost'}
                  className="w-full justify-start"
                >
                  <Link href="/admin/wine-lists">
                    <Wine className="mr-2 h-4 w-4" />
                    Wine Lists
                  </Link>
                </Button>
                <Button
                  asChild
                  variant={isActive('/admin/users') ? 'secondary' : 'ghost'}
                  className="w-full justify-start"
                >
                  <Link href="/admin/users">
                    <Users className="mr-2 h-4 w-4" />
                    Users
                  </Link>
                </Button>
                <Button
                  asChild
                  variant={isActive('/admin/rules') ? 'secondary' : 'ghost'}
                  className="w-full justify-start"
                >
                  <Link href="/admin/rules">
                    <FileText className="mr-2 h-4 w-4" />
                    Rules
                  </Link>
                </Button>
              </>
            )}
          </div>
        </div>
        <Separator />
        <div className="px-3 py-2">
          <h2 className="mb-2 px-4 text-lg font-semibold tracking-tight">
            Settings
          </h2>
          <div className="space-y-1">
            <Button
              asChild
              variant={isActive('/settings') ? 'secondary' : 'ghost'}
              className="w-full justify-start"
            >
              <Link href="/settings">
                <Settings className="mr-2 h-4 w-4" />
                Settings
              </Link>
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
} 