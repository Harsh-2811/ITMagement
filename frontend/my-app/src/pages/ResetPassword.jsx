import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import client from '@/api/client'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Card, CardContent } from '@/components/ui/card'

export default function ResetPassword() {
  const { uidb64, token } = useParams();
  const navigate = useNavigate()
  const [password, setPassword] = useState('')

  const resetMutation = useMutation({
    mutationFn: (data) => client.post(`/reset-password/${uidb64}/${token}/`, data),
    onSuccess: () => {
      alert('Password reset successfully')
      navigate('/')
    },
    onError: (error) => alert(error.response?.data?.error || 'Failed to reset password')
  })

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!password) return alert('Password is required')
    resetMutation.mutate({ password })
  }

  return (
    <div className="flex h-screen items-center justify-center bg-gray-100 dark:bg-gray-900">
      <Card className="w-full max-w-sm shadow-md">
        <CardContent className="space-y-4 p-6">
          <h1 className="text-2xl font-bold text-center">Reset Password</h1>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1">
              <Label htmlFor="password">New Password</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            <Button type="submit" className="w-full">
              Reset Password
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
