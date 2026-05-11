import { BrowserRouter, Routes, Route, Navigate } from 'react-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'sonner'
import { useInitUser } from '../hooks/useInitUser'
import { RequireAuth } from './RequireAuth'
import { RequireRole } from './RequireRole'
import { LoginScreen } from './components/LoginScreen'
import { RegisterScreen } from './components/RegisterScreen'
import { DashboardScreen } from './components/DashboardScreen'
import { DocumentContentScreen } from './components/DocumentContentScreen'
import { DocumentSectionsScreen } from './components/DocumentSectionsScreen'
import { DocumentFormattingScreen } from './components/DocumentFormattingScreen'
import { TemplatesListScreen } from './components/TemplatesListScreen'
import { TemplateEditorScreen } from './components/TemplateEditorScreen'
import { TemplateExtractionScreen } from './components/TemplateExtractionScreen'
import { AdminUsersScreen } from './components/AdminUsersScreen'
import { AdminStatisticsScreen } from './components/AdminStatisticsScreen'
import { NotFoundScreen } from './components/NotFoundScreen'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 30_000 },
  },
})

function AppRoutes() {
  useInitUser()
  return (
    <Routes>
      <Route path="/login" element={<LoginScreen />} />
      <Route path="/register" element={<RegisterScreen />} />

      <Route element={<RequireAuth />}>
        <Route path="/" element={<DashboardScreen />} />
        <Route path="/documents/:id" element={<DocumentContentScreen />} />
        <Route path="/documents/:id/sections" element={<DocumentSectionsScreen />} />
        <Route path="/documents/:id/formatting" element={<DocumentFormattingScreen />} />
        <Route path="/templates" element={<TemplatesListScreen />} />
        <Route path="/templates/extract" element={<TemplateExtractionScreen />} />
        <Route path="/templates/:id" element={<TemplateEditorScreen />} />
      </Route>

      <Route element={<RequireRole role="admin" />}>
        <Route path="/admin" element={<AdminUsersScreen />} />
        <Route path="/admin/statistics" element={<AdminStatisticsScreen />} />
      </Route>

      <Route path="*" element={<NotFoundScreen />} />
    </Routes>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
      <Toaster position="top-right" richColors />
    </QueryClientProvider>
  )
}
