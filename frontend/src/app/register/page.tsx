'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { supabase } from '../../lib/supabaseClient'
import { useAuth } from '@/src/supabase-auth-context'
import axios from 'axios'

export default function Register() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [name, setName] = useState('')
  const [isAdmin, setIsAdmin] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const [loading, setLoading] = useState(false)
  const router = useRouter()
  const { user, loading: authLoading, session } = useAuth()

  // Redirect if already logged in
  if (!authLoading && user) {
    router.replace('/')
    return null
  }

  useEffect(() => {
    if (success) {
      const timeout = setTimeout(() => {
        router.replace('/login')
      }, 2000) // 2 seconds delay
      return () => clearTimeout(timeout)
    }
  }, [success, router])

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const { data, error: signUpError } = await supabase.auth.signUp({
        email,
        password,
      })
      if (signUpError) throw signUpError
      // Wait for session/user to be available
      let supabaseUser = data.user
      if (!supabaseUser) {
        // Try to get the user from the session
        const { data: sessionData } = await supabase.auth.getSession()
        supabaseUser = sessionData.session?.user ?? null
      }
      if (!supabaseUser) throw new Error('No Supabase user found after registration')
      // Call backend to create user row
      await axios.post('/api/users', {
        email,
        name,
        supabase_user_id: supabaseUser.id,
        role: 'staff',
      })
      setSuccess(true)
    } catch (err: any) {
      setError(err.message || 'Registration failed')
    }
    setLoading(false)
  }

  return (
    <div className="flex min-h-[80vh] items-center justify-center bg-background">
      <div className="w-full max-w-md p-8 bg-white rounded-xl shadow-lg border">
        <h2 className="text-2xl font-bold mb-6 text-center">Register</h2>
        <form onSubmit={handleRegister} className="flex flex-col gap-4">
          <div>
            <label htmlFor="email" className="block text-sm font-medium mb-1">Email</label>
            <input id="email" type="email" value={email} onChange={e => setEmail(e.target.value)} required className="w-full rounded-md border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary" autoComplete="email" />
          </div>
          <div>
            <label htmlFor="password" className="block text-sm font-medium mb-1">Password</label>
            <div className="relative">
              <input id="password" type={showPassword ? 'text' : 'password'} value={password} onChange={e => setPassword(e.target.value)} required className="w-full rounded-md border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary pr-10" autoComplete="new-password" />
              <button type="button" tabIndex={-1} className="absolute right-2 top-2 text-xs text-muted-foreground" onClick={() => setShowPassword(v => !v)}>{showPassword ? 'Hide' : 'Show'}</button>
            </div>
          </div>
          <div>
            <label htmlFor="name" className="block text-sm font-medium mb-1">Name</label>
            <input id="name" type="text" value={name} onChange={e => setName(e.target.value)} required className="w-full rounded-md border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary" autoComplete="name" />
          </div>
          <button type="submit" className="w-full bg-primary text-white rounded-md py-2 font-semibold hover:bg-primary/90 transition disabled:opacity-50" disabled={loading}>{loading ? 'Registering...' : 'Register'}</button>
          {error && <div className="text-red-600 text-sm text-center">{error}</div>}
          {success && <div className="text-green-600 text-sm text-center">Registration successful! Redirecting to login...</div>}
        </form>
        <div className="flex justify-center items-center mt-4 text-sm">
          <span>
            Already have an account?{' '}
            <Link href="/login" className="text-primary hover:underline">Login</Link>
          </span>
        </div>
      </div>
    </div>
  )
} 