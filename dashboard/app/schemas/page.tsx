'use client'

import { useEffect, useState } from 'react'
import { Plus, Trash2 } from 'lucide-react'
import { listSchemas, createSchema, deleteSchema } from '@/lib/api'

interface Schema {
  id: string
  name: string
  description?: string
  json_schema: any
  created_at: string
}

export default function SchemasPage() {
  const [schemas, setSchemas] = useState<Schema[]>([])
  const [showCreate, setShowCreate] = useState(false)
  const [newSchema, setNewSchema] = useState({
    name: '',
    description: '',
    json_schema: '{\n  "type": "object",\n  "properties": {}\n}'
  })

  useEffect(() => {
    loadSchemas()
  }, [])

  async function loadSchemas() {
    try {
      const data = await listSchemas()
      setSchemas(data)
    } catch (e) {
      console.error('Failed to load schemas:', e)
    }
  }

  async function handleCreate() {
    try {
      await createSchema({
        name: newSchema.name,
        description: newSchema.description,
        json_schema: JSON.parse(newSchema.json_schema)
      })
      setShowCreate(false)
      setNewSchema({ name: '', description: '', json_schema: '{\n  "type": "object",\n  "properties": {}\n}' })
      loadSchemas()
    } catch (e) {
      alert('Failed to create schema')
    }
  }

  async function handleDelete(id: string) {
    if (!confirm('Delete this schema?')) return
    try {
      await deleteSchema(id)
      loadSchemas()
    } catch (e) {
      alert('Failed to delete schema')
    }
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Schemas</h1>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
        >
          <Plus size={20} />
          Create Schema
        </button>
      </div>

      {showCreate && (
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4">New Schema</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Name</label>
              <input
                type="text"
                value={newSchema.name}
                onChange={(e) => setNewSchema({ ...newSchema, name: e.target.value })}
                className="w-full border rounded-lg px-3 py-2"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Description</label>
              <input
                type="text"
                value={newSchema.description}
                onChange={(e) => setNewSchema({ ...newSchema, description: e.target.value })}
                className="w-full border rounded-lg px-3 py-2"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">JSON Schema</label>
              <textarea
                value={newSchema.json_schema}
                onChange={(e) => setNewSchema({ ...newSchema, json_schema: e.target.value })}
                className="w-full border rounded-lg px-3 py-2 font-mono text-sm h-48"
              />
            </div>
            <div className="flex gap-2">
              <button
                onClick={handleCreate}
                className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
              >
                Create
              </button>
              <button
                onClick={() => setShowCreate(false)}
                className="border px-4 py-2 rounded-lg hover:bg-gray-50"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="bg-white rounded-lg shadow">
        <table className="w-full">
          <thead className="border-b">
            <tr className="text-left">
              <th className="p-4">Name</th>
              <th className="p-4">Description</th>
              <th className="p-4">Created</th>
              <th className="p-4">Actions</th>
            </tr>
          </thead>
          <tbody>
            {schemas.map((schema) => (
              <tr key={schema.id} className="border-b">
                <td className="p-4 font-medium">{schema.name}</td>
                <td className="p-4 text-gray-500">{schema.description || '-'}</td>
                <td className="p-4 text-gray-500">
                  {new Date(schema.created_at).toLocaleDateString()}
                </td>
                <td className="p-4">
                  <button
                    onClick={() => handleDelete(schema.id)}
                    className="text-red-600 hover:text-red-700"
                  >
                    <Trash2 size={18} />
                  </button>
                </td>
              </tr>
            ))}
            {schemas.length === 0 && (
              <tr>
                <td colSpan={4} className="p-4 text-center text-gray-500">
                  No schemas yet
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
