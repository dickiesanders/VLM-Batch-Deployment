'use client'

import { useState } from 'react'
import { Search, RefreshCw } from 'lucide-react'
import { getJob } from '@/lib/api'

interface JobResult {
  job_id: string
  status: string
  processed?: number
  total?: number
  result?: any
  error?: string
}

export default function JobsPage() {
  const [jobId, setJobId] = useState('')
  const [result, setResult] = useState<JobResult | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSearch() {
    if (!jobId) return
    setLoading(true)
    try {
      const data = await getJob(jobId)
      setResult(data)
    } catch (e) {
      alert('Job not found')
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Jobs</h1>

      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Look Up Job</h2>
        <div className="flex gap-2">
          <input
            type="text"
            value={jobId}
            onChange={(e) => setJobId(e.target.value)}
            placeholder="Enter job ID"
            className="flex-1 border rounded-lg px-3 py-2"
          />
          <button
            onClick={handleSearch}
            disabled={loading}
            className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? <RefreshCw size={20} className="animate-spin" /> : <Search size={20} />}
            Search
          </button>
        </div>
      </div>

      {result && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">Job Result</h2>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm text-gray-500">Job ID</label>
                <p className="font-mono">{result.job_id}</p>
              </div>
              <div>
                <label className="text-sm text-gray-500">Status</label>
                <p>
                  <span className={`px-2 py-1 rounded text-sm ${
                    result.status === 'completed' ? 'bg-green-100 text-green-700' :
                    result.status === 'failed' ? 'bg-red-100 text-red-700' :
                    'bg-yellow-100 text-yellow-700'
                  }`}>
                    {result.status}
                  </span>
                </p>
              </div>
              {result.processed !== undefined && (
                <div>
                  <label className="text-sm text-gray-500">Progress</label>
                  <p>{result.processed} / {result.total}</p>
                </div>
              )}
            </div>

            {result.error && (
              <div>
                <label className="text-sm text-gray-500">Error</label>
                <p className="text-red-600">{result.error}</p>
              </div>
            )}

            {result.result && (
              <div>
                <label className="text-sm text-gray-500">Result</label>
                <pre className="bg-gray-50 p-4 rounded-lg overflow-auto text-sm">
                  {JSON.stringify(result.result, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
