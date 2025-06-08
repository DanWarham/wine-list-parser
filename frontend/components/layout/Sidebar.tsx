'use client'

import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import Link from 'next/link'
import { useSession } from 'next-auth/react'
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

interface SidebarProps extends React.HTMLAttributes<HTMLDivElement> {}

export default function Sidebar({ className, ...props }: SidebarProps) {
  const { data: session } = useSession()
  const role = (session?.user as any)?.role
  const pathname = usePathname()

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
                  isActive('/admin/upload') && "bg-accent text-accent-foreground"
                )}>
                  <Link href="/admin/upload">
                    <Upload className="h-4 w-4" />
                    Upload Wine List
                  </Link>
                </Button>
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
        <div className="px-3 py-2">
          <h2 className="mb-2 px-4 text-lg font-semibold tracking-tight">
            Tools
          </h2>
          <div className="space-y-1">
            <Button asChild variant="ghost" className={cn(
              "w-full justify-start gap-2",
              isActive('/parser') && "bg-accent text-accent-foreground"
            )}>
              <Link href="/parser">
                <FileText className="h-4 w-4" />
                Parser
              </Link>
            </Button>
            <Button asChild variant="ghost" className={cn(
              "w-full justify-start gap-2",
              isActive('/export') && "bg-accent text-accent-foreground"
            )}>
              <Link href="/export">
                <Download className="h-4 w-4" />
                Export
              </Link>
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
} 