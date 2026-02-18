// frontend/src/app/admin/roles/components/RoleList.tsx
'use client'

import { useEffect, useState } from 'react'
import { rolesApi, Role } from '@/lib/api'
import { Button } from '@/components/ui/button'
import Link from 'next/link'

export function RoleList() {
  const [roles, setRoles] = useState<Role[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadRoles() {
      try {
        const data = await rolesApi.list()
        setRoles(data)
      } catch (error) {
        console.error('Failed to load roles:', error)
      } finally {
        setLoading(false)
      }
    }
    loadRoles()
  }, [])

  if (loading) return <div>Loading...</div>

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl">Roles ({roles.length})</h2>
        <Button>Create Role</Button>
      </div>

      <div className="grid gap-4">
        {roles.map((role) => (
          <div key={role.id} className="border rounded p-4 flex justify-between items-center">
            <div>
              <h3 className="font-semibold">{role.name}</h3>
              <p className="text-sm text-gray-600">{role.description || 'No description'}</p>
              {role.is_system && (
                <span className="text-xs bg-gray-100 px-2 py-1 rounded">System Role</span>
              )}
            </div>
            <Link href={`/admin/roles/${role.id}`}>
              <Button variant="outline">Edit Permissions</Button>
            </Link>
          </div>
        ))}
      </div>
    </div>
  )
}
