import { useState, useEffect, useRef, type DragEvent } from 'react'
import {
  Upload,
  File,
  Trash2,
  Download,
  AlertCircle,
  Loader2,
  FileText,
  Image,
  Music,
  Video,
  Archive,
  Code
} from 'lucide-react'
import { supabase } from '../lib/supabase'
import type { UploadedFile } from '../types'

const fileTypeIcons: Record<string, React.ElementType> = {
  'text/plain': FileText,
  'application/xml': Code,
  'application/json': Code,
  'image/png': Image,
  'image/jpeg': Image,
  'image/jpg': Image,
  'image/gif': Image,
  'image/webp': Image,
  'audio/mpeg': Music,
  'audio/mp3': Music,
  'video/mp4': Video,
  'application/zip': Archive,
  'application/x-zip-compressed': Archive,
  'application/octet-stream': File,
}

function getFileIcon(fileType: string) {
  return fileTypeIcons[fileType] || File
}

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

export default function FileUploads() {
  const [files, setFiles] = useState<UploadedFile[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const [error, setError] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    fetchFiles()
  }, [])

  async function fetchFiles() {
    setLoading(true)
    const { data, error } = await supabase
      .from('uploaded_files')
      .select('*')
      .order('created_at', { ascending: false })

    if (error) {
      console.error('Error fetching files:', error)
    } else {
      setFiles(data || [])
    }
    setLoading(false)
  }

  async function handleFileUpload(file: File) {
    setUploading(true)
    setError('')

    try {
      const fileExt = file.name.split('.').pop()
      const fileName = `${Date.now()}_${Math.random().toString(36).substring(7)}.${fileExt}`
      const filePath = `uploads/${fileName}`

      const { error: uploadError } = await supabase.storage
        .from('api-files')
        .upload(filePath, file)

      if (uploadError) {
        // Try to create bucket if it doesn't exist
        if (uploadError.message?.includes('bucket')) {
          await supabase.rpc('create_storage_bucket', { bucket_name: 'api-files' })
          const { error: retryError } = await supabase.storage
            .from('api-files')
            .upload(filePath, file)
          if (retryError) throw retryError
        } else {
          throw uploadError
        }
      }

      const { data: publicUrlData } = supabase.storage
        .from('api-files')
        .getPublicUrl(filePath)

      await supabase.from('uploaded_files').insert({
        filename: file.name,
        file_type: file.type || 'application/octet-stream',
        file_size: file.size,
        storage_path: filePath,
        description: null,
        metadata: {
          public_url: publicUrlData?.publicUrl || '',
        },
      })

      fetchFiles()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  async function handleDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault()
    setDragOver(false)

    const droppedFiles = Array.from(e.dataTransfer.files)
    for (const file of droppedFiles) {
      await handleFileUpload(file)
    }
  }

  async function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const selectedFiles = Array.from(e.target.files || [])
    for (const file of selectedFiles) {
      await handleFileUpload(file)
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  async function deleteFile(file: UploadedFile) {
    if (!confirm(`Delete "${file.filename}"?`)) return

    await supabase.storage.from('api-files').remove([file.storage_path])
    await supabase.from('uploaded_files').delete().eq('id', file.id)
    fetchFiles()
  }

  async function downloadFile(file: UploadedFile) {
    const { data, error } = await supabase.storage
      .from('api-files')
      .download(file.storage_path)

    if (error || !data) {
      setError('Download failed')
      return
    }

    const url = URL.createObjectURL(data)
    const a = document.createElement('a')
    a.href = url
    a.download = file.filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary-400" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Upload Area */}
      <div
        onDragOver={(e) => {
          e.preventDefault()
          setDragOver(true)
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
          dragOver
            ? 'border-primary-500 bg-primary-500/10'
            : 'border-slate-700 bg-slate-900/40 hover:border-slate-600 hover:bg-slate-800/40'
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          onChange={handleFileSelect}
          className="hidden"
        />
        <Upload className={`w-10 h-10 mx-auto mb-3 ${dragOver ? 'text-primary-400' : 'text-slate-600'}`} />
        <p className="text-sm text-slate-400 mb-1">
          {uploading ? (
            <span className="flex items-center justify-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" />
              Uploading...
            </span>
          ) : (
            'Drag & drop files here or click to browse'
          )}
        </p>
        <p className="text-xs text-slate-600">APK, XML, JSON, images, audio, video supported</p>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-3 bg-error-500/10 border border-error-500/30 rounded-lg text-sm text-error-400">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      {/* Files List */}
      {files.length === 0 ? (
        <div className="text-center py-12">
          <File className="w-12 h-12 text-slate-700 mx-auto mb-4" />
          <p className="text-slate-500 text-lg">No files uploaded</p>
          <p className="text-slate-600 text-sm mt-1">Upload APK files, config files, or any analysis data</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {files.map((file) => {
            const Icon = getFileIcon(file.file_type)
            return (
              <div
                key={file.id}
                className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 hover:border-slate-700 transition-colors"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className="p-2.5 bg-slate-800/60 rounded-lg">
                      <Icon className="w-5 h-5 text-primary-400" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-white truncate" title={file.filename}>
                        {file.filename}
                      </p>
                      <p className="text-xs text-slate-500">{formatFileSize(file.file_size)}</p>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2 text-xs text-slate-500 mb-3">
                  <span className="px-2 py-0.5 bg-slate-800/60 rounded">{file.file_type}</span>
                </div>

                {file.description && (
                  <p className="text-sm text-slate-400 mb-3">{file.description}</p>
                )}

                <div className="flex gap-2">
                  <button
                    onClick={() => downloadFile(file)}
                    className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 bg-slate-800/60 border border-slate-700 rounded-lg text-xs text-slate-300 hover:bg-slate-700/60 transition-colors"
                  >
                    <Download className="w-3.5 h-3.5" />
                    Download
                  </button>
                  <button
                    onClick={() => deleteFile(file)}
                    className="p-2 bg-error-500/10 border border-error-500/30 rounded-lg text-error-400 hover:bg-error-500/20 transition-colors"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
