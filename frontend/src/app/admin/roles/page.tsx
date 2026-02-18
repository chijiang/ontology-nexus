// frontend/src/app/admin/roles/page.tsx
'use client'

import { ProtectedPage } from '@/components/auth/ProtectedPage'
import { RoleList } from './components/RoleList'

export default function RolesPage() {
  return (
    <ProtectedPage pageId="admin">
      <div className="container mx-auto py-6">
        <h1 className="text-3xl font-bold mb-6">Role Management</h1>
        <RoleList />
      </div>
    </ProtectedPage>
  )
}
