// frontend/src/app/[locale]/admin/roles/[id]/page.tsx
'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import { rolesApi, RoleDetail } from '@/lib/api'
import { ProtectedPage } from '@/components/auth/ProtectedPage'
import { RolePermissionEditor } from '../components/RolePermissionEditor'

export default function RoleDetailPage() {
  const params = useParams()
  const roleId = parseInt(params.id as string)
  const [role, setRole] = useState<RoleDetail | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadRole() {
      try {
        const data = await rolesApi.get(roleId)
        setRole(data)
      } catch (error) {
        console.error('Failed to load role:', error)
      } finally {
        setLoading(false)
      }
    }
    loadRole()
  }, [roleId])

  if (loading) return <div>Loading...</div>
  if (!role) return <div>Role not found</div>

  return (
    <ProtectedPage pageId="admin">
      <div className="container mx-auto py-6">
        <h1 className="text-3xl font-bold mb-6">Edit Role: {role.name}</h1>
        <RolePermissionEditor role={role} />
      </div>
    </ProtectedPage>
  )
}
