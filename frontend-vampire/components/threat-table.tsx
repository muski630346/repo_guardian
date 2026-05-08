'use client'

import { motion } from 'framer-motion'
import { AlertTriangle, Shield, Zap, ExternalLink, Play, Wrench } from 'lucide-react'
import { GlassCard } from './glass-card'
import { cn } from '@/lib/utils'

const threats = [
  {
    id: 1,
    title: 'SQL Injection Vulnerability',
    repo: 'api-gateway/auth-service',
    severity: 'critical',
    type: 'Injection',
    discoveredAt: '2 min ago',
    cwe: 'CWE-89',
    status: 'open',
  },
  {
    id: 2,
    title: 'Hardcoded API Key Exposed',
    repo: 'frontend/payment-module',
    severity: 'high',
    type: 'Secrets',
    discoveredAt: '15 min ago',
    cwe: 'CWE-798',
    status: 'in_progress',
  },
  {
    id: 3,
    title: 'Cross-Site Scripting (XSS)',
    repo: 'web-app/user-dashboard',
    severity: 'high',
    type: 'XSS',
    discoveredAt: '32 min ago',
    cwe: 'CWE-79',
    status: 'open',
  },
  {
    id: 4,
    title: 'Insecure Deserialization',
    repo: 'backend/data-processor',
    severity: 'critical',
    type: 'Deserialization',
    discoveredAt: '1 hour ago',
    cwe: 'CWE-502',
    status: 'open',
  },
  {
    id: 5,
    title: 'Missing Authentication Check',
    repo: 'api-gateway/admin-routes',
    severity: 'medium',
    type: 'AuthZ',
    discoveredAt: '2 hours ago',
    cwe: 'CWE-306',
    status: 'remediated',
  },
]

const severityConfig = {
  critical: {
    bg: 'bg-red-500/20',
    border: 'border-red-500/50',
    text: 'text-red-400',
    glow: 'shadow-[0_0_10px_rgba(239,68,68,0.3)]',
  },
  high: {
    bg: 'bg-orange-500/20',
    border: 'border-orange-500/50',
    text: 'text-orange-400',
    glow: 'shadow-[0_0_10px_rgba(249,115,22,0.3)]',
  },
  medium: {
    bg: 'bg-yellow-500/20',
    border: 'border-yellow-500/50',
    text: 'text-yellow-400',
    glow: 'shadow-[0_0_10px_rgba(234,179,8,0.3)]',
  },
  low: {
    bg: 'bg-blue-500/20',
    border: 'border-blue-500/50',
    text: 'text-blue-400',
    glow: 'shadow-[0_0_10px_rgba(59,130,246,0.3)]',
  },
}

const statusConfig = {
  open: { label: 'Open', color: 'text-red-400' },
  in_progress: { label: 'In Progress', color: 'text-yellow-400' },
  remediated: { label: 'Remediated', color: 'text-emerald-400' },
}

export function ThreatTable() {
  return (
    <GlassCard delay={0.4}>
      <div className="p-6 lg:p-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <div>
            <h2 className="text-xl lg:text-2xl font-bold text-white flex items-center gap-3">
              <AlertTriangle className="w-6 h-6 text-[#8b3a4a]" />
              Threat Intelligence
            </h2>
            <p className="text-white/50 text-sm mt-1">Active vulnerabilities requiring attention</p>
          </div>
          <div className="flex items-center gap-3">
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[#5c1a28]/30 border border-[#5c1a28]/40 text-[#8b3a4a] hover:bg-[#5c1a28]/40 transition-all text-sm font-medium"
            >
              <Play className="w-4 h-4" />
              Run Simulation
            </motion.button>
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-white/10">
                <th className="text-left py-3 px-4 text-xs font-semibold text-white/50 uppercase tracking-wider">Threat</th>
                <th className="text-left py-3 px-4 text-xs font-semibold text-white/50 uppercase tracking-wider hidden md:table-cell">Repository</th>
                <th className="text-left py-3 px-4 text-xs font-semibold text-white/50 uppercase tracking-wider">Severity</th>
                <th className="text-left py-3 px-4 text-xs font-semibold text-white/50 uppercase tracking-wider hidden lg:table-cell">Type</th>
                <th className="text-left py-3 px-4 text-xs font-semibold text-white/50 uppercase tracking-wider hidden sm:table-cell">Status</th>
                <th className="text-right py-3 px-4 text-xs font-semibold text-white/50 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody>
              {threats.map((threat, i) => {
                const severity = severityConfig[threat.severity as keyof typeof severityConfig]
                const status = statusConfig[threat.status as keyof typeof statusConfig]
                
                return (
                  <motion.tr
                    key={threat.id}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.5 + i * 0.1 }}
                    className="border-b border-white/5 hover:bg-white/5 transition-colors group cursor-pointer"
                  >
                    <td className="py-4 px-4">
                      <div className="flex items-center gap-3">
                        <div className={cn(
                          'w-2 h-2 rounded-full animate-pulse',
                          threat.severity === 'critical' ? 'bg-red-500' : 'bg-orange-500'
                        )} />
                        <div>
                          <p className="text-sm font-medium text-white group-hover:text-[#8b3a4a] transition-colors">
                            {threat.title}
                          </p>
                          <p className="text-xs text-white/40 font-mono mt-0.5">{threat.cwe}</p>
                        </div>
                      </div>
                    </td>
                    <td className="py-4 px-4 hidden md:table-cell">
                      <span className="text-sm text-white/60 font-mono">{threat.repo}</span>
                    </td>
                    <td className="py-4 px-4">
                      <span className={cn(
                        'inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold uppercase tracking-wide border',
                        severity.bg,
                        severity.border,
                        severity.text,
                        severity.glow
                      )}>
                        {threat.severity}
                      </span>
                    </td>
                    <td className="py-4 px-4 hidden lg:table-cell">
                      <span className="text-sm text-white/50">{threat.type}</span>
                    </td>
                    <td className="py-4 px-4 hidden sm:table-cell">
                      <span className={cn('text-sm font-medium', status.color)}>
                        {status.label}
                      </span>
                    </td>
                    <td className="py-4 px-4">
                      <div className="flex items-center justify-end gap-2">
                        <motion.button
                          whileHover={{ scale: 1.1 }}
                          whileTap={{ scale: 0.9 }}
                          className="p-2 rounded-lg bg-[#5c1a28]/20 border border-[#5c1a28]/30 text-[#8b3a4a] hover:bg-[#5c1a28]/30 transition-all"
                          title="AI Remediation"
                        >
                          <Wrench className="w-4 h-4" />
                        </motion.button>
                        <motion.button
                          whileHover={{ scale: 1.1 }}
                          whileTap={{ scale: 0.9 }}
                          className="p-2 rounded-lg bg-white/5 border border-white/10 text-white/60 hover:bg-white/10 hover:text-white transition-all"
                          title="View Details"
                        >
                          <ExternalLink className="w-4 h-4" />
                        </motion.button>
                      </div>
                    </td>
                  </motion.tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </GlassCard>
  )
}
