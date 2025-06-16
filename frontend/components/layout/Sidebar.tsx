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

interface SidebarProps extends React.HTMLAttributes<HTMLDivElement> {}

export default function Sidebar({ className, ...props }: SidebarProps) {
  const { user, session } = useAuth()
  const pathname = usePathname()
  const [role, setRole] = useState<string | null>(null)

  useEffect(() => {
    async function fetchRole() {
      if (session?.access_token) {
        try {
          const res = await fetch('/api/me', {
            headers: { Authorization: `Bearer ${session.access_token}` }
          })
          if (res.ok) {
            const data = await res.json()
            setRole(data.role)
          } else {
            setRole(null)
          }
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
    <div className={cn("pb-12 w-64 border-r", className)} {...props}>
      <div className="space-y-4 py-4">
        <div className="px-3 py-2">
          <h2 className="mb-2 px-4 text-lg font-semibold tracking-tight">
            Navigation
          </h2>
          <div className="space-y-1">
            <Button asChild variant="ghost" className={cn(
              "w-full justify-start gap-2",
              isActive(role === 'admin' ? '/admin' : '/search') && "bg-accent text-accent-foreground"
            )}>
              <Link href={role === 'admin' ? '/admin' : '/search'}>
                <LayoutDashboard className="h-4 w-4" />
                {role === 'admin' ? 'Admin Dashboard' : 'Search'}
              </Link>
            </Button>
            {role === 'admin' && (
              <>
                <Button asChild variant="ghost" className={cn(
                  "w-full justify-start gap-2",
                  isActive('/admin/restaurants') && "bg-accent text-accent-foreground"
                )}>
                  <Link href="/admin/restaurants">
                    <Building2 className="h-4 w-4" />
                    Restaurants
                  </Link>
                </Button>
                <Button asChild variant="ghost" className={cn(
                  "w-full justify-start gap-2",
                  isActive('/admin/wine-lists') && "bg-accent text-accent-foreground"
                )}>
                  <Link href="/admin/wine-lists">
                    <Wine className="h-4 w-4" />
                    Wine Lists
                  </Link>
                </Button>
                <Button asChild variant="ghost" className={cn(
                  "w-full justify-start gap-2",
                  isActive('/admin/users') && "bg-accent text-accent-foreground"
                )}>
                  <Link href="/admin/users">
                    <Users className="h-4 w-4" />
                    Users
                  </Link>
                </Button>
                <Button asChild variant="ghost" className={cn(
                  "w-full justify-start gap-2",
                  isActive('/admin/rules') && "bg-accent text-accent-foreground"
                )}>
                  <Link href="/admin/rules">
                    <FileText className="h-4 w-4" />
                    Rules
                  </Link>
                </Button>
              </>
            )}
            <Button asChild variant="ghost" className={cn(
              "w-full justify-start gap-2",
              isActive('/settings') && "bg-accent text-accent-foreground"
            )}>
              <Link href="/settings">
                <Settings className="h-4 w-4" />
                Settings
              </Link>
            </Button>
          </div>
        </div>
        <Separator />
      </div>
    </div>
  )
} 