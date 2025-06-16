'use client'
import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import { useAuth } from '@/src/supabase-auth-context';

export default function ClientLayout({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const isAuthenticated = !!user;

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <div className="flex">
        {isAuthenticated && <Sidebar className="hidden lg:block" />}
        <main className="flex-1 p-6">
          {children}
        </main>
      </div>
    </div>
  );
} 