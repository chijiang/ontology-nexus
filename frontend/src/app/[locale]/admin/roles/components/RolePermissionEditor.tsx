// frontend/src/app/[locale]/admin/roles/components/RolePermissionEditor.tsx
'use client'

import { useState } from 'react'
import { RoleDetail, rolesApi } from '@/lib/api'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'

interface RolePermissionEditorProps {
  role: RoleDetail
}

const ALL_PAGES = ['chat', 'rules', 'actions', 'data-products', 'ontology', 'admin'] as const

export function RolePermissionEditor({ role }: RolePermissionEditorProps) {
  const [loading, setLoading] = useState(false)

  const handleTogglePage = async (pageId: string) => {
    setLoading(true)
    try {
      if (role.page_permissions.includes(pageId)) {
        await rolesApi.removePagePermission(role.id, pageId)
      } else {
        await rolesApi.addPagePermission(role.id, pageId)
      }
      // 重新加载角色数据
      const updated = await rolesApi.get(role.id)
      role = updated
      // 触发重新渲染
      window.location.reload()
    } catch (error) {
      console.error('Failed to toggle page permission:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Tabs defaultValue="pages">
      <TabsList>
        <TabsTrigger value="pages">Page Permissions</TabsTrigger>
        <TabsTrigger value="actions">Action Permissions</TabsTrigger>
        <TabsTrigger value="entities">Entity Permissions</TabsTrigger>
      </TabsList>

      <TabsContent value="pages">
        <div className="space-y-2">
          {ALL_PAGES.map((pageId) => (
            <div key={pageId} className="flex items-center justify-between border p-3 rounded">
              <span className="font-medium">{pageId}</span>
              <Button
                variant={role.page_permissions.includes(pageId) ? 'default' : 'outline'}
                onClick={() => handleTogglePage(pageId)}
                disabled={loading || role.is_system}
              >
                {role.page_permissions.includes(pageId) ? 'Granted' : 'Grant'}
              </Button>
            </div>
          ))}
        </div>
      </TabsContent>

      <TabsContent value="actions">
        <div className="text-sm text-gray-600">
          Action permissions configuration (TODO: implement action selector)
        </div>
      </TabsContent>

      <TabsContent value="entities">
        <div className="text-sm text-gray-600">
          Entity type permissions configuration (TODO: implement entity selector)
        </div>
      </TabsContent>
    </Tabs>
  )
}
