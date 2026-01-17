'use client'

import { useState } from 'react'
import { createClient } from '@/lib/supabase/client'
import { useRouter } from 'next/navigation'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [mode, setMode] = useState<'login' | 'signup' | 'forgot'>('login')

  const router = useRouter()
  const supabase = createClient()

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    const { error } = await supabase.auth.signInWithPassword({
      email,
      password,
    })

    if (error) {
      setError(error.message)
      setLoading(false)
      return
    }

    router.push('/dashboard')
  }

  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    const { error } = await supabase.auth.signUp({
      email,
      password,
    })

    if (error) {
      setError(error.message)
      setLoading(false)
      return
    }

    setError('Check your email for a confirmation link.')
    setLoading(false)
  }

  const handleForgotPassword = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    const { error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/reset-password`,
    })

    if (error) {
      setError(error.message)
      setLoading(false)
      return
    }

    setError('Check your email for a password reset link.')
    setLoading(false)
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-50 to-primary-100 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full">
        <div className="card">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-gray-900">LeverEdge</h1>
            <p className="mt-2 text-gray-600">Client Portal</p>
          </div>

          <form onSubmit={mode === 'login' ? handleLogin : mode === 'signup' ? handleSignUp : handleForgotPassword}>
            <div className="space-y-4">
              <div>
                <label htmlFor="email" className="label">
                  Email address
                </label>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="input"
                  placeholder="you@company.com"
                  required
                />
              </div>

              {mode !== 'forgot' && (
                <div>
                  <label htmlFor="password" className="label">
                    Password
                  </label>
                  <input
                    id="password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="input"
                    placeholder="Enter your password"
                    required
                  />
                </div>
              )}

              {error && (
                <div className={`p-3 rounded-lg text-sm ${
                  error.includes('Check your email')
                    ? 'bg-green-50 text-green-800'
                    : 'bg-red-50 text-red-800'
                }`}>
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading
                  ? 'Please wait...'
                  : mode === 'login'
                  ? 'Sign In'
                  : mode === 'signup'
                  ? 'Create Account'
                  : 'Send Reset Link'}
              </button>
            </div>
          </form>

          <div className="mt-6 text-center text-sm">
            {mode === 'login' && (
              <>
                <button
                  onClick={() => setMode('forgot')}
                  className="text-primary-600 hover:text-primary-500"
                >
                  Forgot your password?
                </button>
                <div className="mt-2">
                  Don&apos;t have an account?{' '}
                  <button
                    onClick={() => setMode('signup')}
                    className="text-primary-600 hover:text-primary-500 font-medium"
                  >
                    Sign up
                  </button>
                </div>
              </>
            )}
            {mode === 'signup' && (
              <div>
                Already have an account?{' '}
                <button
                  onClick={() => setMode('login')}
                  className="text-primary-600 hover:text-primary-500 font-medium"
                >
                  Sign in
                </button>
              </div>
            )}
            {mode === 'forgot' && (
              <button
                onClick={() => setMode('login')}
                className="text-primary-600 hover:text-primary-500"
              >
                Back to sign in
              </button>
            )}
          </div>
        </div>

        <p className="mt-4 text-center text-xs text-gray-500">
          Secure client portal powered by LeverEdge
        </p>
      </div>
    </div>
  )
}
