'use client'

import { useEffect, useState } from 'react'
import { FileText, Briefcase, Box, Zap } from 'lucide-react'

export default function DashboardPage() {
  const [stats, setStats] = useState({
    totalExtractions: 0,
    activeJobs: 0,
    schemas: 0,
    models: 0,
  })

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard
          title="Total Extractions"
          value={stats.totalExtractions}
          icon={Zap}
          color="blue"
        />
        <StatCard
          title="Active Jobs"
          value={stats.activeJobs}
          icon={Briefcase}
          color="green"
        />
        <StatCard
          title="Schemas"
          value={stats.schemas}
          icon={FileText}
          color="purple"
        />
        <StatCard
          title="Models"
          value={stats.models}
          icon={Box}
          color="orange"
        />
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <button className="p-4 border rounded-lg hover:bg-gray-50 text-left">
            <h3 className="font-medium">New Extraction</h3>
            <p className="text-sm text-gray-500">Upload and extract data</p>
          </button>
          <button className="p-4 border rounded-lg hover:bg-gray-50 text-left">
            <h3 className="font-medium">Create Schema</h3>
            <p className="text-sm text-gray-500">Define extraction structure</p>
          </button>
          <button className="p-4 border rounded-lg hover:bg-gray-50 text-left">
            <h3 className="font-medium">Register Model</h3>
            <p className="text-sm text-gray-500">Add custom model</p>
          </button>
        </div>
      </div>
    </div>
  )
}

function StatCard({
  title,
  value,
  icon: Icon,
  color
}: {
  title: string
  value: number
  icon: any
  color: string
}) {
  const colors: Record<string, string> = {
    blue: 'bg-blue-100 text-blue-600',
    green: 'bg-green-100 text-green-600',
    purple: 'bg-purple-100 text-purple-600',
    orange: 'bg-orange-100 text-orange-600',
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-500">{title}</p>
          <p className="text-2xl font-bold">{value}</p>
        </div>
        <div className={`p-3 rounded-lg ${colors[color]}`}>
          <Icon size={24} />
        </div>
      </div>
    </div>
  )
}
