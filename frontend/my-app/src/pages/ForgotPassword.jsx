import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import client from '@/api/client'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Card, CardContent } from '@/components/ui/card'

export default function ForgotPassword() {
  const [email, setEmail] = useState('')
  const forgotMutation = useMutation({
    mutationFn: (data) => client.post('/forgot-password/', data),
    onSuccess: () => alert('Reset link sent to your email'),
    onError: (error) => alert(error.response?.data?.error || 'Failed to send reset link')
  })

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!email) return alert('Email is required')
    forgotMutation.mutate({ email })
  }

  return (
    <div className="flex h-screen items-center justify-center bg-gray-100 dark:bg-gray-900">
      <Card className="w-full max-w-sm shadow-md">
        <CardContent className="space-y-4 p-6">
          <h1 className="text-2xl font-bold text-center">Forgot Password</h1>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
              />
            </div>
            <Button type="submit" className="w-full">
              Send Reset Link
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
