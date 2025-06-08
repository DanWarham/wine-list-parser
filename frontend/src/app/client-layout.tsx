'use client'
import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import { useSession } from 'next-auth/react';

export default function ClientLayout({ children }: { children: React.ReactNode }) {
  const { status } = useSession();
  const isAuthenticated = status === 'authenticated';

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