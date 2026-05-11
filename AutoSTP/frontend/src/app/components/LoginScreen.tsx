import { useState } from 'react'
import { Eye, EyeOff, FileText, Star } from 'lucide-react'
import { useNavigate } from 'react-router'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import { login, getMe } from '../../api/auth'
import { useAuthStore } from '../../store/auth.store'

const schema = z.object({
  email: z.string().email('Invalid email'),
  password: z.string().min(1, 'Password is required'),
})
type FormData = z.infer<typeof schema>

export function LoginScreen() {
  const navigate = useNavigate()
  const setAuth = useAuthStore((s) => s.setAuth)
  const [showPassword, setShowPassword] = useState(false)

  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  const onSubmit = async (data: FormData) => {
    try {
      const tokens = await login(data)
      const me = await getMe()
      setAuth(me, tokens.access_token, tokens.refresh_token)
      navigate('/')
    } catch (err: unknown) {
      const status = (err as { response?: { status: number } }).response?.status
      toast.error(status === 401 ? 'Invalid email or password' : 'Login failed. Try again.')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: '#F8FAFC' }}>
      <div className="bg-white rounded-lg shadow-lg p-8 w-full max-w-[400px]">
        <div className="flex flex-col items-center mb-8">
          <div className="relative mb-3">
            <FileText size={48} style={{ color: '#2563EB' }} />
            <Star size={20} style={{ color: '#2563EB', position: 'absolute', top: 0, right: -8 }} />
          </div>
          <p className="text-sm" style={{ color: '#6B7280' }}>
            Automated academic paper formatting BSUIR
          </p>
        </div>

        <h2 className="mb-6" style={{ color: '#111827' }}>Sign In</h2>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label className="block mb-2" style={{ color: '#111827' }}>Email</label>
            <input
              {...register('email')}
              type="email"
              placeholder="your@email.com"
              className="w-full px-3 py-2 border rounded-md"
              style={{ borderColor: errors.email ? '#DC2626' : '#E5E7EB', borderRadius: '6px', height: '44px' }}
            />
            {errors.email && <p className="text-xs mt-1" style={{ color: '#DC2626' }}>{errors.email.message}</p>}
          </div>

          <div>
            <label className="block mb-2" style={{ color: '#111827' }}>Password</label>
            <div className="relative">
              <input
                {...register('password')}
                type={showPassword ? 'text' : 'password'}
                placeholder="••••••••"
                className="w-full px-3 py-2 border rounded-md pr-10"
                style={{ borderColor: errors.password ? '#DC2626' : '#E5E7EB', borderRadius: '6px', height: '44px' }}
              />
              <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-3 top-1/2 -translate-y-1/2" style={{ color: '#6B7280' }}>
                {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
              </button>
            </div>
            {errors.password && <p className="text-xs mt-1" style={{ color: '#DC2626' }}>{errors.password.message}</p>}
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full text-white rounded-md flex items-center justify-center"
            style={{ backgroundColor: isSubmitting ? '#93C5FD' : '#2563EB', borderRadius: '6px', height: '44px', cursor: isSubmitting ? 'not-allowed' : 'pointer' }}
          >
            {isSubmitting ? 'Signing in...' : 'Sign In'}
          </button>

          <p className="text-center text-sm" style={{ color: '#6B7280' }}>
            Don't have an account?{' '}
            <button type="button" onClick={() => navigate('/register')} className="hover:underline" style={{ color: '#2563EB' }}>
              Register
            </button>
          </p>
        </form>
      </div>
    </div>
  )
}
