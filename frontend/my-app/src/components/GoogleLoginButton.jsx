import { GoogleLogin } from '@react-oauth/google'
import { useMutation } from '@tanstack/react-query'
import client from '@/api/client'
import { useNavigate } from 'react-router-dom'

export default function GoogleLoginButton() {
  const navigate = useNavigate()

  const mutation = useMutation({
    mutationFn: (token) =>
      client.post('/google-login/', { access_token: token }),
    onSuccess: (res) => {
      const { access, refresh, user } = res.data
      localStorage.setItem('access', access)
      localStorage.setItem('refresh', refresh)
      localStorage.setItem('user', JSON.stringify(user))

      if (user.user_type === 'admin') {
        navigate('/admin-dashboard')
      } else {
        navigate('/dashboard')
      }
    },
    onError: () => alert('Google login failed'),
  })

  return (
    <GoogleLogin
      onSuccess={(credentialResponse) => {
        const token = credentialResponse.credential
        if (token) mutation.mutate(token)
      }}
      onError={() => alert('Google Sign-In was unsuccessful')}
      // useOneTap
    />
  ) 
}
