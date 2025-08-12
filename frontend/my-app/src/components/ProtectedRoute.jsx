import { Navigate } from 'react-router-dom';

export default function ProtectedRoute({ children }) {
  const isAuthenticated = !!localStorage.getItem('access');
  return isAuthenticated ? children : <Navigate to="/" replace />;
}
