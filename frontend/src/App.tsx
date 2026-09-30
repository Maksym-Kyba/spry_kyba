import { Navigate, Route, Routes } from 'react-router'
import { HomePage } from '@/components/home-page'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/home" replace />} />
      <Route path="/home" element={<HomePage />} />
      <Route path="*" element={<Navigate to="/home" replace />} />
    </Routes>
  )
}
