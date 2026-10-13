import { Navigate, Route, Routes } from 'react-router'
import { hasAuthParams, useAuth } from 'react-oidc-context'

import { HomePage } from '@/components/home-page'
import { LoginPage } from '@/components/login-page'
import { isAuthEnabled } from '@/lib/auth'

function RootRoute() {
  const auth = useAuth()

  // Do not navigate away before AuthProvider has finished processing ?code= and ?state=
  if (isAuthEnabled && (auth.isLoading || hasAuthParams())) {
    return (
      <div className="flex min-h-svh items-center justify-center p-4">
        <p className="text-muted-foreground text-sm">Signing in...</p>
      </div>
    )
  }

  return <Navigate to="/home" replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<RootRoute />} />
      <Route path="/home" element={<HomePage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/login/" element={<LoginPage />} />
      <Route path="*" element={<Navigate to="/home" replace />} />
    </Routes>
  )
}
