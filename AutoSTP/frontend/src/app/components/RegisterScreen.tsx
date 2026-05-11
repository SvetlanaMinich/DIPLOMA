import { useState } from 'react'
import { Eye, EyeOff, FileText, Star } from 'lucide-react'
import { useNavigate } from 'react-router'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import { register as apiRegister, login, getMe } from '../../api/auth'
import { useAuthStore } from '../../store/auth.store'

const schema = z.object({
  full_name: z.string().min(2, 'Name must be at least 2 characters'),
  email: z.string().email('Invalid email'),
  password: z.string()
    .min(8, 'Minimum 8 characters')
    .regex(/[A-Z]/, 'Must contain uppercase letter')
    .regex(/[0-9]/, 'Must contain a digit'),
  confirm_password: z.string(),
}).refine((d) => d.password === d.confirm_password, {
  message: 'Passwords do not match',
  path: ['confirm_password'],
})
type FormData = z.infer<typeof schema>

export function RegisterScreen() {
  const navigate = useNavigate()
  const setAuth = useAuthStore((s) => s.setAuth)
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)

  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  const onSubmit = async (data: FormData) => {
    try {
      await apiRegister({ email: data.email, password: data.password, full_name: data.full_name })
      const tokens = await login({ email: data.email, password: data.password })
      const me = await getMe()
      setAuth(me, tokens.access_token, tokens.refresh_token)
      navigate('/')
    } catch (err: unknown) {
      const status = (err as { response?: { status: number } }).response?.status
      toast.error(status === 409 ? 'Email already taken' : 'Registration failed. Try again.')
    }
  }

  const field = (name: keyof FormData) => ({
    style: { borderColor: errors[name] ? '#DC2626' : '#E5E7EB', borderRadius: '6px', height: '44px' },
    className: 'w-full px-3 py-2 border rounded-md',
  })

  return (
    <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: '#F8FAFC' }}>
      <div className="bg-white rounded-lg shadow-lg p-8 w-full max-w-[400px]">
        <div className="flex flex-col items-center mb-8">
          <div className="relative mb-3">
            <FileText size={48} style={{ color: '#2563EB' }} />
            <Star size={20} style={{ color: '#2563EB', position: 'absolute', top: 0, right: -8 }} />
          </div>
        </div>

        <h2 className="mb-6" style={{ color: '#111827' }}>Create Account</h2>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label className="block mb-2" style={{ color: '#111827' }}>Full Name</label>
            <input {...register('full_name')} type="text" placeholder="John Doe" {...field('full_name')} />
            {errors.full_name && <p className="text-xs mt-1" style={{ color: '#DC2626' }}>{errors.full_name.message}</p>}
          </div>

          <div>
            <label className="block mb-2" style={{ color: '#111827' }}>Email</label>
            <input {...register('email')} type="email" placeholder="your@email.com" {...field('email')} />
            {errors.email && <p className="text-xs mt-1" style={{ color: '#DC2626' }}>{errors.email.message}</p>}
          </div>

          <div>
            <label className="block mb-2" style={{ color: '#111827' }}>Password</label>
            <div className="relative">
              <input {...register('password')} type={showPassword ? 'text' : 'password'} placeholder="••••••••" {...field('password')} style={{ ...field('password').style, paddingRight: '40px' }} />
              <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-3 top-1/2 -translate-y-1/2" style={{ color: '#6B7280' }}>
                {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
              </button>
            </div>
            {errors.password && <p className="text-xs mt-1" style={{ color: '#DC2626' }}>{errors.password.message}</p>}
          </div>

          <div>
            <label className="block mb-2" style={{ color: '#111827' }}>Confirm Password</label>
            <div className="relative">
              <input {...register('confirm_password')} type={showConfirm ? 'text' : 'password'} placeholder="••••••••" {...field('confirm_password')} style={{ ...field('confirm_password').style, paddingRight: '40px' }} />
              <button type="button" onClick={() => setShowConfirm(!showConfirm)} className="absolute right-3 top-1/2 -translate-y-1/2" style={{ color: '#6B7280' }}>
                {showConfirm ? <EyeOff size={20} /> : <Eye size={20} />}
              </button>
            </div>
            {errors.confirm_password && <p className="text-xs mt-1" style={{ color: '#DC2626' }}>{errors.confirm_password.message}</p>}
          </div>

          <p className="text-xs" style={{ color: '#6B7280' }}>
            Minimum 8 characters, one uppercase letter and one digit
          </p>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full text-white rounded-md"
            style={{ backgroundColor: isSubmitting ? '#93C5FD' : '#2563EB', borderRadius: '6px', height: '44px', cursor: isSubmitting ? 'not-allowed' : 'pointer' }}
          >
            {isSubmitting ? 'Creating account...' : 'Register'}
          </button>

          <p className="text-center text-sm" style={{ color: '#6B7280' }}>
            Already have an account?{' '}
            <button type="button" onClick={() => navigate('/login')} className="hover:underline" style={{ color: '#2563EB' }}>
              Sign In
            </button>
          </p>
        </form>
      </div>
    </div>
  )
}
