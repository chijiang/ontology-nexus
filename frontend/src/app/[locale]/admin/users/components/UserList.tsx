// frontend/src/app/[locale]/admin/users/components/UserList.tsx
'use client'

import { useEffect, useState } from 'react'
import { usersApi, User } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { UserCreateDialog } from './UserCreateDialog'

export function UserList() {
  const [users, setUsers] = useState<User[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)

  const loadUsers = async () => {
    setLoading(true)
    try {
      const response = await usersApi.list()
      setUsers(response.items)
      setTotal(response.total)
    } catch (error) {
      console.error('Failed to load users:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadUsers()
  }, [])

  if (loading) return <div>Loading...</div>

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl">Users ({total})</h2>
        <Button onClick={() => setShowCreate(true)}>Create User</Button>
      </div>

      <table className="w-full">
        <thead>
          <tr className="border-b">
            <th className="text-left p-2">Username</th>
            <th className="text-left p-2">Email</th>
            <th className="text-left p-2">Status</th>
            <th className="text-left p-2">Admin</th>
            <th className="text-left p-2">Actions</th>
          </tr>
        </thead>
        <tbody>
          {users.map((user) => (
            <tr key={user.id} className="border-b">
              <td className="p-2">{user.username}</td>
              <td className="p-2">{user.email || '-'}</td>
              <td className="p-2">
                <span className={`px-2 py-1 rounded text-sm ${
                  user.approval_status === 'approved' ? 'bg-green-100 text-green-800' :
                  user.approval_status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                  'bg-red-100 text-red-800'
                }`}>
                  {user.approval_status}
                </span>
              </td>
              <td className="p-2">{user.is_admin ? 'Yes' : 'No'}</td>
              <td className="p-2">
                <Button variant="ghost" size="sm">Edit</Button>
                <Button variant="ghost" size="sm">Reset Password</Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {showCreate && (
        <UserCreateDialog
          onClose={() => setShowCreate(false)}
          onCreated={loadUsers}
        />
      )}
    </div>
  )
}
