'use client'

import { useEffect, useState } from 'react'
import { Plus, Trash2, Play } from 'lucide-react'
import { listModels, registerModel, deleteModel, fetchAPI } from '@/lib/api'

interface Model {
  id: string
  name: string
  source: string
  model_id: string
  is_active: boolean
  is_default: boolean
  total_requests: number
  created_at: string
}

export default function ModelsPage() {
  const [models, setModels] = useState<Model[]>([])
  const [showCreate, setShowCreate] = useState(false)
  const [newModel, setNewModel] = useState({
    name: '',
    source: 'huggingface',
    model_id: '',
    hf_token: '',
    gpu_memory_utilization: 0.85,
    max_model_len: 4096,
    is_default: false
  })

  useEffect(() => {
    loadModels()
  }, [])

  async function loadModels() {
    try {
      const data = await listModels()
      setModels(data)
    } catch (e) {
      console.error('Failed to load models:', e)
    }
  }

  async function handleCreate() {
    try {
      await registerModel(newModel)
      setShowCreate(false)
      setNewModel({
        name: '',
        source: 'huggingface',
        model_id: '',
        hf_token: '',
        gpu_memory_utilization: 0.85,
        max_model_len: 4096,
        is_default: false
      })
      loadModels()
    } catch (e) {
      alert('Failed to register model')
    }
  }

  async function handleDelete(id: string) {
    if (!confirm('Delete this model?')) return
    try {
      await deleteModel(id)
      loadModels()
    } catch (e) {
      alert('Failed to delete model')
    }
  }

  async function handleLoad(id: string) {
    try {
      await fetchAPI(`/models/${id}/load`, { method: 'POST' })
      alert('Model loaded successfully')
    } catch (e) {
      alert('Failed to load model')
    }
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Models (BYOM)</h1>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
        >
          <Plus size={20} />
          Register Model
        </button>
      </div>

      {showCreate && (
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4">Register New Model</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Name</label>
              <input
                type="text"
                value={newModel.name}
                onChange={(e) => setNewModel({ ...newModel, name: e.target.value })}
                className="w-full border rounded-lg px-3 py-2"
                placeholder="my-fine-tuned-model"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Source</label>
              <select
                value={newModel.source}
                onChange={(e) => setNewModel({ ...newModel, source: e.target.value })}
                className="w-full border rounded-lg px-3 py-2"
              >
                <option value="huggingface">HuggingFace</option>
                <option value="local">Local</option>
                <option value="external">External Endpoint</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Model ID</label>
              <input
                type="text"
                value={newModel.model_id}
                onChange={(e) => setNewModel({ ...newModel, model_id: e.target.value })}
                className="w-full border rounded-lg px-3 py-2"
                placeholder="org/model-name"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">HF Token (optional)</label>
              <input
                type="password"
                value={newModel.hf_token}
                onChange={(e) => setNewModel({ ...newModel, hf_token: e.target.value })}
                className="w-full border rounded-lg px-3 py-2"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">GPU Memory %</label>
              <input
                type="number"
                value={newModel.gpu_memory_utilization}
                onChange={(e) => setNewModel({ ...newModel, gpu_memory_utilization: parseFloat(e.target.value) })}
                className="w-full border rounded-lg px-3 py-2"
                step="0.05"
                min="0.1"
                max="1"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Max Model Length</label>
              <input
                type="number"
                value={newModel.max_model_len}
                onChange={(e) => setNewModel({ ...newModel, max_model_len: parseInt(e.target.value) })}
                className="w-full border rounded-lg px-3 py-2"
              />
            </div>
            <div className="col-span-2">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={newModel.is_default}
                  onChange={(e) => setNewModel({ ...newModel, is_default: e.target.checked })}
                />
                Set as default model
              </label>
            </div>
            <div className="col-span-2 flex gap-2">
              <button
                onClick={handleCreate}
                className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
              >
                Register
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
              <th className="p-4">Source</th>
              <th className="p-4">Model ID</th>
              <th className="p-4">Requests</th>
              <th className="p-4">Status</th>
              <th className="p-4">Actions</th>
            </tr>
          </thead>
          <tbody>
            {models.map((model) => (
              <tr key={model.id} className="border-b">
                <td className="p-4 font-medium">
                  {model.name}
                  {model.is_default && (
                    <span className="ml-2 text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">
                      Default
                    </span>
                  )}
                </td>
                <td className="p-4">{model.source}</td>
                <td className="p-4 text-gray-500 font-mono text-sm">{model.model_id}</td>
                <td className="p-4">{model.total_requests}</td>
                <td className="p-4">
                  <span className={`text-xs px-2 py-1 rounded ${
                    model.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'
                  }`}>
                    {model.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
                <td className="p-4">
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleLoad(model.id)}
                      className="text-blue-600 hover:text-blue-700"
                      title="Load model"
                    >
                      <Play size={18} />
                    </button>
                    <button
                      onClick={() => handleDelete(model.id)}
                      className="text-red-600 hover:text-red-700"
                      title="Delete"
                    >
                      <Trash2 size={18} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {models.length === 0 && (
              <tr>
                <td colSpan={6} className="p-4 text-center text-gray-500">
                  No models registered
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
