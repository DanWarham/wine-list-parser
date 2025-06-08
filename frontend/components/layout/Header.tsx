import { Menu, Wine } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet'
import { useSession } from 'next-auth/react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import UserMenu from '@/components/UserMenu'
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

export default function Header() {
  const { data: session } = useSession()
  const pathname = usePathname()
  const role = (session?.user as any)?.role

  const isActive = (path: string) => pathname === path

  const navItems = [
    {
      href: role === 'admin' ? '/admin' : '/search',
      label: role === 'admin' ? 'Admin Dashboard' : 'Search',
      icon: LayoutDashboard
    },
    ...(role === 'admin' ? [
      {
        href: '/admin/upload',
        label: 'Upload Wine List',
        icon: Upload
      },
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

  const toolItems = [
    {
      href: '/parser',
      label: 'Parser',
      icon: FileText
    },
    {
      href: '/export',
      label: 'Export',
      icon: Download
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
                <div className="px-3 py-2">
                  <h2 className="mb-2 px-4 text-lg font-semibold tracking-tight">
                    Tools
                  </h2>
                  <div className="space-y-1">
                    {toolItems.map((item) => (
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
            <Link href="/parser" className="text-sm font-medium transition-colors hover:text-primary">
              Parser
            </Link>
            <Link href="/export" className="text-sm font-medium transition-colors hover:text-primary">
              Export
            </Link>
          </nav>
          <UserMenu />
        </div>
      </div>
    </header>
  )
} 