import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import client from '@/api/client';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Card, CardContent } from '@/components/ui/card';


export default function ChangePassword() {
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const navigate = useNavigate();

  const changeMutation = useMutation({
    mutationFn: (data) =>
      client.post('/change-password/', data, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('access')}`,
        },
      }),
    onSuccess: () => {
      alert('Password changed. Please log in again.');

    },
    onError: (err) =>
      alert(err.response?.data?.error || 'Failed to change password'),
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!currentPassword || !newPassword)
      return alert('Both fields are required');
    changeMutation.mutate({
      current_password: currentPassword,
      new_password: newPassword,
    });
  };

  return (
    <div className="flex h-screen items-center justify-center bg-gray-100 dark:bg-gray-900">
      <Card className="w-full max-w-sm shadow-md">
        <CardContent className="space-y-4 p-6">
          <h1 className="text-2xl font-bold text-center">Change Password</h1>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1">
              <Label htmlFor="current">Current Password</Label>
              <Input
                id="current"
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                required
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="new">New Password</Label>
              <Input
                id="new"
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
              />
            </div>
            <Button type="submit" className="w-full">
              Update Password
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
