import { Upload, Zap, Loader2 } from 'lucide-react'
import { useNavigate } from 'react-router'
import { useState, useRef } from 'react'
import { useMutation } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Sidebar } from './Sidebar'
import { extractTemplate } from '../../api/templates'
import type { TemplateOut } from '../../types/template'

export function TemplateExtractionScreen() {
  const navigate = useNavigate()
  const [file, setFile] = useState<File | null>(null)
  const [name, setName] = useState('')
  const [result, setResult] = useState<TemplateOut | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  const extractMut = useMutation({
    mutationFn: () => extractTemplate(file!, name || undefined),
    onSuccess: (t) => {
      setResult(t)
      toast.success('Template extracted successfully')
    },
    onError: (e: unknown) => {
      const status = (e as { response?: { status: number } }).response?.status
      toast.error(status === 400 ? 'Unsupported file format' : status === 413 ? 'File too large (max 10 MB)' : 'Extraction failed. Try again.')
    },
  })

  const previewRows = result
    ? Object.entries(result.template_json).slice(0, 10).map(([k, v]) => ({
        key: k,
        value: typeof v === 'object' ? JSON.stringify(v) : String(v),
      }))
    : []

  return (
    <div className="flex h-screen" style={{ backgroundColor: '#F8FAFC' }}>
      <Sidebar />
      <div className="flex-1 overflow-auto">
        <div className="p-8">
          <div className="mb-8">
            <h1 className="mb-3" style={{ color: '#111827' }}>Create Template from Standard</h1>
            <p style={{ color: '#6B7280' }}>Upload a formatting standard document — LLM will automatically extract all formatting rules</p>
          </div>

          <div className="max-w-2xl mx-auto">
            {extractMut.isPending ? (
              <div className="bg-white rounded-lg shadow-md p-8" style={{ borderRadius: '8px' }}>
                <div className="flex flex-col items-center text-center">
                  <Loader2 size={48} style={{ color: '#2563EB' }} className="mb-4 animate-spin" />
                  <p className="mb-6" style={{ color: '#111827' }}>LLM is analyzing the document...</p>
                  <div className="w-full mb-4">
                    <div className="h-2 rounded-full overflow-hidden" style={{ backgroundColor: '#E5E7EB' }}>
                      <div
                        className="h-full rounded-full"
                        style={{ backgroundColor: '#2563EB', width: '60%', animation: 'pulse 2s ease-in-out infinite' }}
                      />
                    </div>
                  </div>
                  <p className="text-sm" style={{ color: '#6B7280' }}>Extracting formatting rules... This may take up to 3 minutes.</p>
                </div>
              </div>
            ) : result ? (
              <div className="bg-white rounded-lg shadow-md p-8" style={{ borderRadius: '8px' }}>
                <div className="flex items-center gap-3 p-4 rounded-lg mb-6" style={{ backgroundColor: '#16A34A10', border: '1px solid #16A34A' }}>
                  <span style={{ color: '#16A34A' }}>✓ Template successfully extracted from {file?.name}</span>
                </div>
                <h3 className="mb-4" style={{ color: '#111827' }}>Extracted Parameters (preview)</h3>
                <table className="w-full mb-8">
                  <tbody>
                    {previewRows.map((row, i) => (
                      <tr key={i} className="border-b" style={{ borderColor: '#E5E7EB' }}>
                        <td className="py-3 pr-8 w-1/3" style={{ color: '#6B7280' }}>{row.key}</td>
                        <td className="py-3" style={{ color: '#111827', wordBreak: 'break-all' }}>{row.value}</td>
                      </tr>
                    ))}
                    {Object.keys(result.template_json).length > 10 && (
                      <tr>
                        <td colSpan={2} className="py-3 text-sm" style={{ color: '#6B7280' }}>
                          ...and {Object.keys(result.template_json).length - 10} more parameters
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
                <div className="flex gap-3">
                  <button
                    onClick={() => navigate(`/templates/${result.id}`)}
                    className="flex-1 text-white rounded-md"
                    style={{ backgroundColor: '#2563EB', borderRadius: '6px', height: '44px' }}
                  >
                    Open Template
                  </button>
                  <button
                    onClick={() => { setResult(null); setFile(null); setName('') }}
                    className="flex-1 border rounded-md"
                    style={{ borderColor: '#2563EB', color: '#2563EB', borderRadius: '6px', height: '44px' }}
                  >
                    Extract Another
                  </button>
                </div>
              </div>
            ) : (
              <>
                <div
                  className="border-2 border-dashed rounded-lg p-12 mb-6 cursor-pointer hover:border-blue-400 transition-colors"
                  style={{ borderColor: file ? '#2563EB' : '#E5E7EB', borderRadius: '8px' }}
                  onClick={() => fileRef.current?.click()}
                >
                  <div className="flex flex-col items-center text-center">
                    <Upload size={48} style={{ color: '#6B7280' }} className="mb-4" />
                    {file ? (
                      <p style={{ color: '#111827' }}>{file.name}</p>
                    ) : (
                      <>
                        <p className="mb-2" style={{ color: '#111827' }}>Drop file here or click to select</p>
                        <p className="text-sm" style={{ color: '#6B7280' }}>PDF, DOCX, TXT · Max 10 MB</p>
                      </>
                    )}
                  </div>
                  <input
                    ref={fileRef}
                    type="file"
                    accept=".pdf,.docx,.txt"
                    className="hidden"
                    onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                  />
                </div>

                <div className="mb-6">
                  <label className="block mb-2" style={{ color: '#111827' }}>Template Name (optional)</label>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g., GOST Template 2024"
                    className="w-full px-3 py-2 border rounded-md"
                    style={{ borderColor: '#E5E7EB', borderRadius: '6px', height: '44px' }}
                  />
                </div>

                <button
                  disabled={!file}
                  onClick={() => extractMut.mutate()}
                  className="w-full text-white rounded-md flex items-center justify-center gap-2"
                  style={{ backgroundColor: !file ? '#93C5FD' : '#2563EB', borderRadius: '6px', height: '44px', cursor: !file ? 'not-allowed' : 'pointer' }}
                >
                  <Zap size={20} /> Extract Template
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
