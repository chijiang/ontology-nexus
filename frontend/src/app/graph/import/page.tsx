// frontend/src/app/graph/import/page.tsx
'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { AppLayout } from '@/components/layout'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { graphApi } from '@/lib/api'
import { useAuthStore } from '@/lib/auth'
import { toast } from 'sonner'
import { Upload } from 'lucide-react'

export default function ImportPage() {
  const router = useRouter()
  const token = useAuthStore((state) => state.token)
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any>(null)

  if (!token) {
    router.push('/')
    return null
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0])
    }
  }

  const handleImport = async () => {
    if (!file) return

    setLoading(true)
    try {
      const res = await graphApi.import(file, token)
      setResult(res.data)
      toast.success('图谱导入成功！')
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '导入失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AppLayout>
      <div className="max-w-2xl mx-auto">
        <h1 className="text-2xl font-bold mb-6">导入 OWL 图谱</h1>

        <Card>
          <CardHeader>
            <CardTitle>上传文件</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="border-2 border-dashed rounded-lg p-8 text-center">
              <Upload className="h-12 w-12 mx-auto mb-4 text-gray-400" />
              <input
                type="file"
                accept=".ttl,.owl,.rdf"
                onChange={handleFileChange}
                className="hidden"
                id="file-upload"
              />
              <label htmlFor="file-upload" className="cursor-pointer">
                <span className="text-blue-600 hover:underline">
                  点击选择文件
                </span>
                <span className="text-gray-400 ml-2">或拖拽文件到此处</span>
              </label>
              {file && (
                <p className="mt-2 text-sm text-gray-600">已选择: {file.name}</p>
              )}
            </div>

            <Button onClick={handleImport} disabled={!file || loading} className="w-full">
              {loading ? '导入中...' : '开始导入'}
            </Button>

            {result && (
              <div className="mt-4 p-4 bg-green-50 rounded-lg">
                <h3 className="font-semibold text-green-800">导入成功！</h3>
                <p className="text-sm text-green-700">
                  Schema: {result.schema_stats.classes} 个类,
                  {result.schema_stats.properties} 个属性
                </p>
                <p className="text-sm text-green-700">
                  Instance: {result.instance_stats.nodes} 个节点,
                  {result.instance_stats.relationships} 个关系
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </AppLayout>
  )
}
