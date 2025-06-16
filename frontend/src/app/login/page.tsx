'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { supabase } from '../../lib/supabaseClient'
import { useAuth } from '@/src/supabase-auth-context'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const router = useRouter()
  const { user, loading: authLoading } = useAuth()

  if (!authLoading && user) {
    return null
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const { data, error: signInError } = await supabase.auth.signInWithPassword({
        email,
        password,
      })
      if (signInError) throw signInError
      const session = data.session
      const token = session?.access_token
      const res = await fetch('/api/me', {
        headers: { Authorization: `Bearer ${token}` }
      })
      const userInfo = await res.json()
      if (userInfo.role === 'admin') {
        await router.push('/admin')
      } else {
        await router.push('/search')
      }
    } catch (err: any) {
      setError('Invalid credentials')
    }
    setLoading(false)
  }

  return (
    <div className="flex min-h-[80vh] items-center justify-center bg-background">
      <div className="w-full max-w-md p-8 bg-white rounded-xl shadow-lg border">
        <h2 className="text-2xl font-bold mb-6 text-center">Login</h2>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label htmlFor="email" className="block text-sm font-medium mb-1">Email</label>
            <input id="email" type="email" value={email} onChange={e => setEmail(e.target.value)} required className="w-full rounded-md border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary" autoComplete="email" />
          </div>
          <div>
            <label htmlFor="password" className="block text-sm font-medium mb-1">Password</label>
            <div className="relative">
              <input id="password" type={showPassword ? 'text' : 'password'} value={password} onChange={e => setPassword(e.target.value)} required className="w-full rounded-md border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary pr-10" autoComplete="current-password" />
              <button type="button" tabIndex={-1} className="absolute right-2 top-2 text-xs text-muted-foreground" onClick={() => setShowPassword(v => !v)}>{showPassword ? 'Hide' : 'Show'}</button>
            </div>
          </div>
          <button type="submit" className="w-full bg-primary text-white rounded-md py-2 font-semibold hover:bg-primary/90 transition disabled:opacity-50" disabled={loading}>{loading ? 'Logging in...' : 'Login'}</button>
          {error && <div className="text-red-600 text-sm text-center">{error}</div>}
        </form>
        <div className="flex justify-between items-center mt-4 text-sm">
          <Link href="/forgot-password" className="text-primary hover:underline">Forgot password?</Link>
          <span>
            Don&apos;t have an account?{' '}
            <Link href="/register" className="text-primary hover:underline">Register here</Link>
          </span>
        </div>
      </div>
    </div>
  )
} 