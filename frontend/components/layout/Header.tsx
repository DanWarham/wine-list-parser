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

export default function Header() {
  const { user, session } = useAuth()
  const pathname = usePathname()

  const isActive = (path: string) => pathname === path

  const navItems = [
    {
      href: session?.access_token ? '/admin' : '/search',
      label: session?.access_token ? 'Admin Dashboard' : 'Search',
      icon: LayoutDashboard
    },
    ...(session?.access_token ? [
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
      <div className="container flex h-16 items-center justify-between">
        <div className="flex items-center gap-6">
          <Sheet>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon" className="lg:hidden">
                <Menu className="h-5 w-5" />
                <span className="sr-only">Toggle Menu</span>
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-[300px] sm:w-[400px]">
              <div className="flex flex-col space-y-4 py-4">
                <div className="px-3 py-2">
                  <h2 className="mb-2 px-4 text-lg font-semibold tracking-tight">
                    Navigation
                  </h2>
                  <div className="space-y-1">
                    {navItems.map((item) => (
                      <Button
                        key={item.href}
                        asChild
                        variant="ghost"
                        className={cn(
                          "w-full justify-start gap-2",
                          isActive(item.href) && "bg-accent text-accent-foreground"
                        )}
                      >
                        <Link href={item.href}>
                          <item.icon className="h-4 w-4" />
                          {item.label}
                        </Link>
                      </Button>
                    ))}
                  </div>
                </div>
              </div>
            </SheetContent>
          </Sheet>
          <Link href="/" className="flex items-center gap-2">
            <Wine className="h-6 w-6 text-primary" />
            <span className="hidden font-bold sm:inline-block">Wine List Parser</span>
          </Link>
        </div>
        
        <div className="flex items-center gap-4">
          <nav className="hidden items-center gap-6 lg:flex">
            <Link href="/search" className="text-sm font-medium transition-colors hover:text-primary">
              Search
            </Link>
          </nav>
          <UserMenu />
        </div>
      </div>
    </header>
  )
} 