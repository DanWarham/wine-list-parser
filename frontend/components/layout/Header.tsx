import { Menu, Wine } from 'lucide-react'
import { Button } from '../ui/button'
import { Sheet, SheetContent, SheetTrigger } from '../ui/sheet'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { 
  Search, 
  Upload, 
  Building2, 
  Users, 
  Settings, 
  FileText, 
  Download,
  LayoutDashboard
} from 'lucide-react'
import { useAuth } from '@/src/supabase-auth-context'
import UserMenu from '@/components/UserMenu'
import { useEffect, useState } from 'react'
import { api } from '@/utils/api_v2'

export default function Header() {
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

  const navItems = [
    {
      href: role === 'admin' ? '/admin' : '/search',
      label: role === 'admin' ? 'Admin Dashboard' : 'Search',
      icon: LayoutDashboard
    },
    ...(role === 'admin' ? [
      {
        href: '/admin/restaurants',
        label: 'Restaurants',
        icon: Building2
      },
      {
        href: '/admin/wine-lists',
        label: 'Wine Lists',
        icon: Wine
      },
      {
        href: '/admin/users',
        label: 'Users',
        icon: Users
      },
      {
        href: '/admin/rules',
        label: 'Rules',
        icon: FileText
      }
    ] : []),
    {
      href: '/settings',
      label: 'Settings',
      icon: Settings
    }
  ]

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-14 items-center">
        <div className="mr-4 hidden md:flex">
          <Link href="/" className="mr-6 flex items-center space-x-2">
            <Wine className="h-6 w-6" />
            <span className="hidden font-bold sm:inline-block">
              Wine List Parser
            </span>
          </Link>
          <nav className="flex items-center space-x-6 text-sm font-medium">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "transition-colors hover:text-foreground/80",
                  isActive(item.href) ? "text-foreground" : "text-foreground/60"
                )}
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
        <Sheet>
          <SheetTrigger asChild>
            <Button
              variant="ghost"
              className="mr-2 px-0 text-base hover:bg-transparent focus-visible:bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0 md:hidden"
            >
              <Menu className="h-6 w-6" />
              <span className="sr-only">Toggle Menu</span>
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="pr-0">
            <Link href="/" className="flex items-center">
              <Wine className="mr-2 h-6 w-6" />
              <span className="font-bold">Wine List Parser</span>
            </Link>
            <nav className="flex flex-col space-y-4 mt-4">
              {navItems.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "flex items-center text-sm font-medium transition-colors hover:text-foreground/80",
                    isActive(item.href) ? "text-foreground" : "text-foreground/60"
                  )}
                >
                  <item.icon className="mr-2 h-4 w-4" />
                  {item.label}
                </Link>
              ))}
            </nav>
          </SheetContent>
        </Sheet>
        <div className="flex flex-1 items-center justify-between space-x-2 md:justify-end">
          <div className="w-full flex-1 md:w-auto md:flex-none">
            {/* Add search bar here if needed */}
          </div>
          <nav className="flex items-center">
            {user ? (
              <UserMenu />
            ) : (
              <Button asChild variant="ghost" size="sm">
                <Link href="/login">Login</Link>
              </Button>
            )}
          </nav>
        </div>
      </div>
    </header>
  )
} 