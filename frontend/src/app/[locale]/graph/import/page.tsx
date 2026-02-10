// frontend/src/app/graph/import/page.tsx
'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useTranslations } from 'next-intl'
import { AppLayout } from '@/components/layout'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { graphApi } from '@/lib/api'
import { useAuthStore } from '@/lib/auth'
import { toast } from 'sonner'
import { Upload, Trash2, AlertTriangle } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"

export default function ImportPage() {
  const router = useRouter()
  const t = useTranslations()
  const token = useAuthStore((state) => state.token)
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [isHydrated, setIsHydrated] = useState(false)
  const [showClearDialog, setShowClearDialog] = useState(false)

  useEffect(() => {
    setIsHydrated(true)
  }, [])

  useEffect(() => {
    if (isHydrated && !token) {
      router.push('/')
    }
  }, [isHydrated, token, router])

  if (!isHydrated || !token) {
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
      toast.success(t('graph.import.clearSuccess'))
    } catch (err: any) {
      toast.error(err.response?.data?.detail || t('graph.import.importFailed'))
    } finally {
      setLoading(false)
    }
  }

  const handleClear = async (clearOntology: boolean) => {
    setLoading(true)
    try {
      await graphApi.clear(clearOntology)
      setResult(null)
      toast.success(clearOntology ? t('graph.import.clearAll') : t('graph.import.clearInstances'))
      setShowClearDialog(false)
    } catch (err: any) {
      toast.error(err.response?.data?.detail || t('graph.import.clearFailed'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <AppLayout>
      <div className="max-w-2xl mx-auto">
        <h1 className="text-2xl font-bold mb-6">{t('graph.import.title')}</h1>

        <Card>
          <CardHeader>
            <CardTitle>{t('graph.import.uploadFile')}</CardTitle>
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
                  {t('graph.import.selectFile')}
                </span>
                <span className="text-gray-400 ml-2">{t('graph.import.dragFile')}</span>
              </label>
              {file && (
                <p className="mt-2 text-sm text-gray-600">{t('graph.import.selected')}: {file.name}</p>
              )}
            </div>

            <Button onClick={handleImport} disabled={!file || loading} className="w-full">
              {loading ? t('common.loading') : t('graph.import.startImport')}
            </Button>

            <Dialog open={showClearDialog} onOpenChange={setShowClearDialog}>
              <DialogTrigger asChild>
                <Button variant="outline" disabled={loading} className="w-full text-red-500 hover:text-red-600 hover:bg-red-50">
                  <Trash2 className="w-4 h-4 mr-2" />
                  {t('graph.import.clearGraph')}
                </Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-[425px] justify-items-center">
                <DialogHeader className="flex flex-col items-center text-center sm:text-center w-full">
                  <DialogTitle className="flex items-center justify-center text-red-600 w-full text-center">
                    <AlertTriangle className="w-5 h-5 mr-2" />
                    {t('graph.import.clearConfirmTitle')}
                  </DialogTitle>
                  <DialogDescription className="text-center w-full">
                    {t('graph.import.clearConfirmDesc')}
                  </DialogDescription>
                </DialogHeader>
                <div className="flex flex-col gap-4 py-4 w-full items-center">
                  <Button
                    variant="outline"
                    className="w-full flex h-auto py-4 px-4 border border-gray-300 hover:bg-red-50 hover:text-red-600 hover:border-red-300 justify-center text-center"
                    onClick={() => handleClear(false)}
                    disabled={loading}
                  >
                    <div className="flex flex-col items-center justify-center gap-1 text-center w-full">
                      <span className="font-bold text-base text-center">{t('graph.import.clearInstances')}</span>
                      <span className="text-sm opacity-80 font-normal text-center">{t('graph.import.clearInstancesDesc')}</span>
                    </div>
                  </Button>
                  <Button
                    variant="destructive"
                    className="w-full flex h-auto py-4 px-4 justify-center text-center"
                    onClick={() => handleClear(true)}
                    disabled={loading}
                  >
                    <div className="flex flex-col items-center justify-center gap-1 text-center w-full">
                      <span className="font-bold text-base text-center">{t('graph.import.clearAll')}</span>
                      <span className="text-sm opacity-90 font-normal text-center">{t('graph.import.clearAllDesc')}</span>
                    </div>
                  </Button>
                </div>
                <DialogFooter className="flex justify-center sm:justify-center w-full">
                  <Button variant="ghost" onClick={() => setShowClearDialog(false)} disabled={loading} className="mx-auto">
                    {t('common.cancel')}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>

            {result && (
              <div className="mt-4 p-4 bg-green-50 rounded-lg">
                <h3 className="font-semibold text-green-800">{t('graph.import.importSuccess')}</h3>
                <p className="text-sm text-green-700">
                  {t('graph.import.schemaStats')}: {result.schema_stats.classes} {t('graph.import.classes')},
                  {result.schema_stats.properties} {t('graph.import.properties')}
                </p>
                <p className="text-sm text-green-700">
                  {t('graph.import.instanceStats')}: {result.instance_stats.nodes} {t('graph.import.nodes')},
                  {result.instance_stats.relationships} {t('graph.import.relationships')}
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </AppLayout>
  )
}
