import React from 'react'
import {
  AuthContext,
  AuthProvider,
  type AuthContextProps,
  type AuthProviderProps,
} from 'react-oidc-context'

export const isAuthEnabled = Boolean(
  import.meta.env.VITE_COGNITO_AUTHORITY &&
  import.meta.env.VITE_COGNITO_CLIENT_ID &&
  import.meta.env.VITE_COGNITO_DOMAIN,
)

export const cognitoAuthConfig: AuthProviderProps = {
  authority: import.meta.env.VITE_COGNITO_AUTHORITY ?? '',
  client_id: import.meta.env.VITE_COGNITO_CLIENT_ID ?? '',
  redirect_uri: `${window.location.origin}/`,
  response_type: 'code',
  scope: 'email openid profile',
  onSigninCallback: () => {
    window.history.replaceState({}, document.title, window.location.pathname)
  },
}

const noopAuth: AuthContextProps = {
  isLoading: false,
  isAuthenticated: false,
  user: null,
  error: undefined,
  activeNavigator: undefined,
  settings: {} as unknown as AuthContextProps['settings'],
  events: {} as unknown as AuthContextProps['events'],
  clearStaleState: async () => {},
  removeUser: async () => {},
  signinPopup: async () => {
    throw new Error('Auth not configured')
  },
  signinSilent: async () => null,
  signinRedirect: async () => {
    console.warn('Cognito authentication is not configured in this environment.')
  },
  signinResourceOwnerCredentials: async () => {
    throw new Error('Auth not configured')
  },
  signoutRedirect: async () => {},
  signoutPopup: async () => {},
  signoutSilent: async () => {},
  querySessionStatus: async () => null,
  revokeTokens: async () => {},
  startSilentRenew: () => {},
  stopSilentRenew: () => {},
}

export function AppAuthProvider({ children }: { children: React.ReactNode }) {
  if (!isAuthEnabled) {
    return <AuthContext.Provider value={noopAuth}>{children}</AuthContext.Provider>
  }
  return <AuthProvider {...cognitoAuthConfig}>{children}</AuthProvider>
}

export async function signOut(auth: AuthContextProps) {
  await auth.removeUser()
  const domain = import.meta.env.VITE_COGNITO_DOMAIN
  const clientId = import.meta.env.VITE_COGNITO_CLIENT_ID
  const logoutUri = `${window.location.origin}/`

  if (domain && clientId) {
    const cognitoLogoutUrl = `https://${domain}/logout?client_id=${encodeURIComponent(clientId)}&logout_uri=${encodeURIComponent(logoutUri)}`
    window.location.href = cognitoLogoutUrl
  } else {
    window.location.href = '/'
  }
}
