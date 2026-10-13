import { useEffect, useRef } from 'react'
import { Link, Navigate } from 'react-router'
import { useAuth } from 'react-oidc-context'

import { Button } from '@/components/ui/button'
import { isAuthEnabled } from '@/lib/auth'

export function LoginPage() {
  const auth = useAuth()
  const redirectedRef = useRef(false)

  useEffect(() => {
    if (!isAuthEnabled || auth.isLoading || auth.isAuthenticated || redirectedRef.current) {
      return
    }
    redirectedRef.current = true
    void auth.signinRedirect()
  }, [auth.isLoading, auth.isAuthenticated, auth])

  if (auth.isAuthenticated) {
    return <Navigate to="/home" replace />
  }

  if (!isAuthEnabled) {
    return (
      <div className="flex min-h-svh flex-col items-center justify-center gap-3 p-4">
        <p className="text-muted-foreground text-sm">Authentication is not configured.</p>
        <Button variant="outline" asChild>
          <Link to="/home">Return to Home</Link>
        </Button>
      </div>
    )
  }

  if (auth.error) {
    return (
      <div className="flex min-h-svh flex-col items-center justify-center gap-3 p-4">
        <p className="text-destructive text-sm">Sign in error: {auth.error.message}</p>
        <Button variant="outline" asChild>
          <Link to="/home">Return to Home</Link>
        </Button>
      </div>
    )
  }

  return (
    <div className="flex min-h-svh items-center justify-center p-4">
      <p className="text-muted-foreground text-sm">Redirecting to sign in...</p>
    </div>
  )
}
