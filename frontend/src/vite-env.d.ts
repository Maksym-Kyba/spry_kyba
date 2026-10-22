interface ImportMetaEnv {
  readonly VITE_API_URL?: string
  readonly VITE_COGNITO_AUTHORITY?: string
  readonly VITE_COGNITO_CLIENT_ID?: string
  readonly VITE_COGNITO_DOMAIN?: string
  readonly VITE_PARSER_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
