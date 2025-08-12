import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import client from '@/api/client'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Card, CardContent } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import GoogleLoginButton from '@/components/GoogleLoginButton'

export default function Login() {
  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [agreed, setAgreed] = useState(false)
  const navigate = useNavigate()

  // Prevent login if already authenticated
  useEffect(() => {
    const access = localStorage.getItem('access')
    if (access) {
      navigate('/dashboard')
    }
  }, [navigate])

  // React Query mutation
  const loginMutation = useMutation({
    mutationFn: (payload) => client.post('/login/', payload),
    onSuccess: ({ data }) => {
      const { access, refresh, user } = data
      localStorage.setItem('access', access)
      localStorage.setItem('refresh', refresh)
      localStorage.setItem('user', JSON.stringify(user))

      if (user.user_type === 'admin') {
        navigate('/admin-dashboard')
      } else {
        navigate('/dashboard')
      }
    },
    onError: (error) => {
      alert(error.response?.data?.error || 'Login failed')
    },
  })

  const handleLogin = (e) => {
    e.preventDefault()
    if (localStorage.getItem('access')) {
      alert('You are already logged in.')
      return
    }

    if (!identifier || !password || !agreed) {
      alert('Fill in all fields and accept terms')
      return
    }

    loginMutation.mutate({ username: identifier, password })
  }

  return (
    <div className="flex h-screen items-center justify-center bg-gray-100 dark:bg-gray-900 px-4">
      <Card className="w-full max-w-sm shadow-md">
        <CardContent className="space-y-4 p-6">
          <h1 className="text-2xl font-bold text-center">Login</h1>
          <form onSubmit={handleLogin} className="space-y-4">
            <div className="space-y-1">
              <Label htmlFor="identifier">Username or Email</Label>
              <Input
                id="identifier"
                type="text"
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
                placeholder="you@example.com or username"
                required
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            <div className="flex items-center space-x-2">
              <Checkbox
                id="terms"
                checked={agreed}
                onCheckedChange={(checked) => setAgreed(checked)}
              />
              <Label htmlFor="terms">Accept terms and conditions</Label>
            </div>

            <Button
              type="submit"
              className="w-full"
              disabled={loginMutation.isPending}
            >
              {loginMutation.isPending ? 'Signing in...' : 'Sign In'}
            </Button>
          </form>

          <div className="text-center text-sm text-gray-500">or</div>

          <div className="flex justify-center">
            <GoogleLoginButton />
          </div>

          <div className="flex justify-end">
            <a
              href="/forgot-password"
              className="text-sm text-blue-600 hover:underline"
            >
              Forgot password?
            </a>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
