// frontend/src/hooks/usePermissions.ts
import { useEffect, useState } from 'react'
import { useAuthStore } from '@/lib/auth'
import { usersApi } from '@/lib/api'

export function usePermissions() {
  const { user, token, setPermissions } = useAuthStore()
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadPermissions() {
      if (!token || !user) {
        setLoading(false)
        return
      }

      try {
        const permissions = await usersApi.getMyPermissions()
        setPermissions(permissions)
      } catch (error) {
        console.error('Failed to load permissions:', error)
      } finally {
        setLoading(false)
      }
    }

    loadPermissions()
  }, [token, user, setPermissions])

  const permissions = useAuthStore((state) => state.permissions)

  const hasPageAccess = (pageId: string): boolean => {
    if (!permissions) return false
    if (permissions.is_admin) return true
    return permissions.accessible_pages.includes(pageId)
  }

  const hasActionPermission = (entityType: string, actionName: string): boolean => {
    if (!permissions) return false
    if (permissions.is_admin) return true
    const actions = permissions.accessible_actions[entityType]
    return actions?.includes(actionName) ?? false
  }

  const hasEntityAccess = (entityClassName: string): boolean => {
    if (!permissions) return false
    if (permissions.is_admin) return true
    return permissions.accessible_entities.includes(entityClassName)
  }

  return {
    permissions,
    loading,
    hasPageAccess,
    hasActionPermission,
    hasEntityAccess,
  }
}
