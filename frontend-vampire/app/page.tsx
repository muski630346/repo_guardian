'use client'

import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import {
  ShieldCheck,
  TrendingDown,
  Activity,
  Users,
  Clock,
  AlertTriangle,
} from 'lucide-react'

import { AnimatedBackground } from '@/components/animated-background'
import { Navbar } from '@/components/navbar'
import { MetricCard } from '@/components/metric-card'
import { MiniChart } from '@/components/mini-chart'
import { AIAgentsNetwork } from '@/components/ai-agents-network'
import { ThreatTable } from '@/components/threat-table'
import { RemediationEngine } from '@/components/remediation-engine'
import { ActivityFeed } from '@/components/activity-feed'
import { AICopilot } from '@/components/ai-copilot'

import { getDashboardData } from '@/lib/api'

export default function DashboardPage() {
  const [dashboardData, setDashboardData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadDashboard() {
      try {
        const data = await getDashboardData()

        console.log('Dashboard API:', data)

        setDashboardData(data)
      } catch (err) {
        console.error('Dashboard API Error:', err)
      } finally {
        setLoading(false)
      }
    }

    loadDashboard()

    const interval = setInterval(loadDashboard, 5000)

    return () => clearInterval(interval)
  }, [])

  if (loading || !dashboardData) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center overflow-hidden">
        <div className="text-center">
          <div className="w-24 h-24 rounded-full border-4 border-[#8b0000] border-t-transparent animate-spin mx-auto mb-8" />

          <h1 className="text-4xl font-bold text-white mb-3">
            RepoGuardian AI
          </h1>

          <p className="text-[#8b3a4a] text-lg animate-pulse">
            Initializing Security Command Center...
          </p>
        </div>
      </div>
    )
  }

  const metrics = [
    {
      title: 'Risk Reduction',
      value: `${dashboardData.risk_reduction || 0}%`,
      change: 12,
      changeLabel: 'vs last month',
      icon: TrendingDown,
      color: 'green' as const,
      chartData: [40, 35, 45, 30, 25, 20, 15, 10, 8, 6],
    },

    {
      title: 'Compliance Score',
      value: `${dashboardData.compliance_score || 0}%`,
      change: 3,
      changeLabel: 'SOC 2 Type II',
      icon: ShieldCheck,
      color: 'red' as const,
      chartData: [85, 88, 90, 92, 94, 95, 96, 97, 98, 98],
    },

    {
      title: 'Security Health',
      value: dashboardData.security_health || 'A+',
      change: 8,
      changeLabel: 'Excellent rating',
      icon: Activity,
      color: 'green' as const,
      chartData: [70, 75, 78, 82, 85, 88, 92, 95, 97, 99],
    },

    {
      title: 'Active Agents',
      value: String(dashboardData.active_agents || 0),
      change: 4,
      changeLabel: 'All systems nominal',
      icon: Users,
      color: 'blue' as const,
      chartData: [18, 19, 20, 21, 22, 22, 23, 23, 24, 24],
    },

    {
      title: 'Mean Detection',
      value: dashboardData.mean_detection_time || '0s',
      change: -28,
      changeLabel: 'Response time',
      icon: Clock,
      color: 'green' as const,
      chartData: [5, 4.5, 4, 3.5, 3, 2.5, 2, 1.8, 1.5, 1.2],
    },

    {
      title: 'Open Findings',
      value: String(dashboardData.open_findings || 0),
      change: -45,
      changeLabel: `${dashboardData.critical_findings || 0} critical`,
      icon: AlertTriangle,
      color: 'red' as const,
      chartData: [25, 22, 18, 15, 12, 10, 9, 8, 7, 7],
    },
  ]

  return (
    <div className="min-h-screen bg-[#050505] text-white overflow-hidden">
      <AnimatedBackground />

      <Navbar />

      <main className="relative pt-24 lg:pt-28 pb-12 px-4 lg:px-8 max-w-[1800px] mx-auto">
        {/* HERO */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7 }}
          className="mb-10"
        >
          <div className="inline-flex items-center gap-3 px-4 py-2 rounded-full border border-white/10 bg-[#1a0005]/50 backdrop-blur-xl mb-6">
            <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />

            <span className="text-sm text-white/70">
              Autonomous AI Security System Active
            </span>
          </div>

          <h1 className="text-4xl lg:text-6xl font-black text-white mb-4 leading-tight">
            Security{' '}
            <span className="text-[#8b0000] drop-shadow-[0_0_30px_rgba(139,0,0,0.9)]">
              Command Center
            </span>
          </h1>

          <p className="text-white/50 text-lg lg:text-xl max-w-3xl leading-relaxed">
            Real-time AI-powered repository protection with autonomous threat
            detection, remediation, pull request governance, and enterprise
            cyber intelligence.
          </p>
        </motion.div>

        {/* METRICS */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-5 mb-10">
          {metrics.map((metric, i) => (
            <MetricCard
              key={metric.title}
              title={metric.title}
              value={metric.value}
              change={metric.change}
              changeLabel={metric.changeLabel}
              icon={metric.icon}
              color={metric.color}
              delay={i * 0.08}
              chart={
                <MiniChart
                  data={metric.chartData}
                  color={
                    metric.color === 'green'
                      ? '#10b981'
                      : metric.color === 'blue'
                      ? '#3b82f6'
                      : '#8b0000'
                  }
                />
              }
            />
          ))}
        </div>

        {/* AI AGENTS */}
        <div className="mb-10">
          <AIAgentsNetwork />
        </div>

        {/* THREAT + REMEDIATION */}
        <div className="grid lg:grid-cols-2 gap-8 mb-10">
          <ThreatTable />
          <RemediationEngine />
        </div>

        {/* LIVE ACTIVITY */}
        <div className="mb-10">
          <ActivityFeed />
        </div>
      </main>

      {/* AI COPILOT */}
      <AICopilot />
    </div>
  )
}