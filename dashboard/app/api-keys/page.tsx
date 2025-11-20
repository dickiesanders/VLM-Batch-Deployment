'use client'

import { useState, useEffect } from 'react'
import { Copy, Eye, EyeOff } from 'lucide-react'

export default function APIKeysPage() {
  const [apiKey, setApiKey] = useState('')
  const [showKey, setShowKey] = useState(false)

  useEffect(() => {
    const saved = localStorage.getItem('api_key')
    if (saved) setApiKey(saved)
  }, [])

  function handleSave() {
    localStorage.setItem('api_key', apiKey)
    alert('API key saved')
  }

  function handleCopy() {
    navigator.clipboard.writeText(apiKey)
    alert('Copied to clipboard')
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">API Keys</h1>

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">Your API Key</h2>
        <p className="text-gray-500 mb-4">
          Enter your API key to authenticate requests from this dashboard.
          Format: <code className="bg-gray-100 px-1">tenant-id:secret-key</code>
        </p>

        <div className="flex gap-2 mb-4">
          <div className="flex-1 relative">
            <input
              type={showKey ? 'text' : 'password'}
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="tenant-123:your-secret-key"
              className="w-full border rounded-lg px-3 py-2 pr-20"
            />
            <div className="absolute right-2 top-1/2 -translate-y-1/2 flex gap-1">
              <button
                onClick={() => setShowKey(!showKey)}
                className="p-1 text-gray-400 hover:text-gray-600"
              >
                {showKey ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
              <button
                onClick={handleCopy}
                className="p-1 text-gray-400 hover:text-gray-600"
              >
                <Copy size={18} />
              </button>
            </div>
          </div>
          <button
            onClick={handleSave}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
          >
            Save
          </button>
        </div>

        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <p className="text-sm text-yellow-800">
            <strong>Note:</strong> In production, API keys would be generated and managed
            server-side with proper encryption and rotation policies.
          </p>
        </div>
      </div>
    </div>
  )
}
