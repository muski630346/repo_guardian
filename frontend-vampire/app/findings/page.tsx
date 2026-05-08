'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { 
  AlertTriangle, 
  Filter, 
  Play, 
  Shield,
  Clock,
  GitBranch,
  ChevronRight,
  Flame,
  Bug,
  Key,
  Code
} from 'lucide-react'
import { AnimatedBackground } from '@/components/animated-background'
import { Navbar } from '@/components/navbar'
import { GlassCard } from '@/components/glass-card'
import { cn } from '@/lib/utils'

const findings = [
  {
    id: 1,
    title: 'SQL Injection in User Authentication',
    description: 'Unsanitized user input is being directly concatenated into SQL query strings.',
    severity: 'critical',
    category: 'Injection',
    icon: Bug,
    repo: 'api-gateway/auth-service',
    file: 'src/controllers/auth.ts',
    line: 47,
    cwe: 'CWE-89',
    cvss: 9.8,
    discoveredAt: '2 hours ago',
    status: 'open',
    attackVector: 'Network',
  },
  {
    id: 2,
    title: 'Hardcoded AWS Secret Key',
    description: 'Production AWS credentials found in source code repository.',
    severity: 'critical',
    category: 'Secrets',
    icon: Key,
    repo: 'infrastructure/terraform',
    file: 'modules/s3/main.tf',
    line: 23,
    cwe: 'CWE-798',
    cvss: 9.1,
    discoveredAt: '4 hours ago',
    status: 'in_progress',
    attackVector: 'Local',
  },
  {
    id: 3,
    title: 'Cross-Site Scripting (Reflected)',
    description: 'User-controlled input is reflected in HTML response without proper encoding.',
    severity: 'high',
    category: 'XSS',
    icon: Code,
    repo: 'web-frontend/dashboard',
    file: 'pages/search.tsx',
    line: 156,
    cwe: 'CWE-79',
    cvss: 7.4,
    discoveredAt: '1 day ago',
    status: 'open',
    attackVector: 'Network',
  },
  {
    id: 4,
    title: 'Insecure Deserialization',
    description: 'Untrusted data is being deserialized without proper validation.',
    severity: 'high',
    category: 'Deserialization',
    icon: Flame,
    repo: 'backend/data-processor',
    file: 'src/utils/serializer.ts',
    line: 89,
    cwe: 'CWE-502',
    cvss: 8.1,
    discoveredAt: '2 days ago',
    status: 'open',
    attackVector: 'Network',
  },
  {
    id: 5,
    title: 'Missing Authentication on Admin Endpoint',
    description: 'Administrative API endpoint accessible without authentication.',
    severity: 'medium',
    category: 'AuthZ',
    icon: Shield,
    repo: 'api-gateway/admin-routes',
    file: 'src/routes/admin.ts',
    line: 34,
    cwe: 'CWE-306',
    cvss: 6.5,
    discoveredAt: '3 days ago',
    status: 'remediated',
    attackVector: 'Network',
  },
]

const severityConfig = {
  critical: {
    bg: 'bg-red-500/20',
    border: 'border-red-500/50',
    text: 'text-red-400',
    glow: 'shadow-[0_0_20px_rgba(239,68,68,0.3)]',
    bar: 'bg-red-500',
  },
  high: {
    bg: 'bg-orange-500/20',
    border: 'border-orange-500/50',
    text: 'text-orange-400',
    glow: 'shadow-[0_0_20px_rgba(249,115,22,0.3)]',
    bar: 'bg-orange-500',
  },
  medium: {
    bg: 'bg-yellow-500/20',
    border: 'border-yellow-500/50',
    text: 'text-yellow-400',
    glow: 'shadow-[0_0_20px_rgba(234,179,8,0.3)]',
    bar: 'bg-yellow-500',
  },
  low: {
    bg: 'bg-blue-500/20',
    border: 'border-blue-500/50',
    text: 'text-blue-400',
    glow: 'shadow-[0_0_20px_rgba(59,130,246,0.3)]',
    bar: 'bg-blue-500',
  },
}

const statusLabels = {
  open: 'Open',
  in_progress: 'In Progress',
  remediated: 'Remediated',
}

export default function FindingsPage() {
  const [activeFilter, setActiveFilter] = useState<string | null>(null)

  const filteredFindings = activeFilter
    ? findings.filter((f) => f.severity === activeFilter)
    : findings

  const severityCounts = {
    critical: findings.filter((f) => f.severity === 'critical').length,
    high: findings.filter((f) => f.severity === 'high').length,
    medium: findings.filter((f) => f.severity === 'medium').length,
    low: findings.filter((f) => f.severity === 'low').length,
  }

  return (
    <div className="min-h-screen bg-[#050505] text-white">
      <AnimatedBackground />
      <Navbar />
      
      <main className="relative pt-24 lg:pt-28 pb-12 px-4 lg:px-8 max-w-[1800px] mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8 lg:mb-12"
        >
          <h1 className="text-3xl lg:text-5xl font-bold text-white mb-3">
            Security <span className="text-[#8b3a4a] text-glow">Findings</span>
          </h1>
          <p className="text-white/50 text-lg max-w-2xl">
            Comprehensive vulnerability analysis and threat intelligence.
            Prioritized by risk score and business impact.
          </p>
        </motion.div>

        {/* Severity Heatmap */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="mb-8 lg:mb-12"
        >
          <GlassCard delay={0.1}>
            <div className="p-6">
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-[#8b3a4a]" />
                Severity Distribution
              </h3>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                {Object.entries(severityCounts).map(([severity, count], i) => {
                  const config = severityConfig[severity as keyof typeof severityConfig]
                  const isActive = activeFilter === severity
                  
                  return (
                    <motion.button
                      key={severity}
                      initial={{ opacity: 0, scale: 0.9 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: 0.2 + i * 0.1 }}
                      onClick={() => setActiveFilter(isActive ? null : severity)}
                      className={cn(
                        'p-4 rounded-xl border transition-all',
                        config.bg,
                        config.border,
                        isActive && config.glow,
                        'hover:scale-[1.02]'
                      )}
                    >
                      <p className={cn('text-3xl font-bold', config.text)}>{count}</p>
                      <p className="text-sm text-white/50 capitalize mt-1">{severity}</p>
                      <div className={cn('h-1 rounded-full mt-3', config.bar, 'opacity-50')} 
                        style={{ width: `${(count / findings.length) * 100}%` }} 
                      />
                    </motion.button>
                  )
                })}
              </div>
            </div>
          </GlassCard>
        </motion.div>

        {/* Actions Bar */}
        <div className="flex flex-wrap items-center gap-4 mb-6">
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[#5c1a28]/30 border border-[#5c1a28]/40 text-[#8b3a4a] hover:bg-[#5c1a28]/40 transition-all text-sm font-medium"
          >
            <Play className="w-4 h-4" />
            Attack Simulation
          </motion.button>
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-white/5 border border-white/10 text-white/70 hover:bg-white/10 transition-all text-sm font-medium"
          >
            <Filter className="w-4 h-4" />
            Filters
          </motion.button>
          {activeFilter && (
            <motion.button
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              onClick={() => setActiveFilter(null)}
              className="text-sm text-white/50 hover:text-white transition-colors"
            >
              Clear filter
            </motion.button>
          )}
        </div>

        {/* Findings List */}
        <div className="space-y-4">
          {filteredFindings.map((finding, i) => {
            const severity = severityConfig[finding.severity as keyof typeof severityConfig]
            const Icon = finding.icon

            return (
              <motion.div
                key={finding.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3 + i * 0.1 }}
              >
                <GlassCard delay={0.3 + i * 0.1}>
                  <div className="p-4 lg:p-6">
                    <div className="flex flex-col lg:flex-row lg:items-start gap-4 lg:gap-6">
                      {/* Icon */}
                      <div className={cn(
                        'w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0',
                        severity.bg,
                        severity.border,
                        'border'
                      )}>
                        <Icon className={cn('w-6 h-6', severity.text)} />
                      </div>

                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <div className="flex flex-wrap items-center gap-2 mb-2">
                          <span className={cn(
                            'px-2 py-0.5 rounded text-xs font-semibold uppercase',
                            severity.bg,
                            severity.text
                          )}>
                            {finding.severity}
                          </span>
                          <span className="text-xs text-white/40 font-mono">{finding.cwe}</span>
                          <span className="text-xs text-white/40">•</span>
                          <span className="text-xs text-white/40">CVSS: {finding.cvss}</span>
                          <span className={cn(
                            'text-xs font-medium',
                            finding.status === 'remediated' ? 'text-emerald-400' :
                            finding.status === 'in_progress' ? 'text-yellow-400' : 'text-red-400'
                          )}>
                            {statusLabels[finding.status as keyof typeof statusLabels]}
                          </span>
                        </div>

                        <h3 className="text-lg font-semibold text-white mb-2 group-hover:text-[#8b3a4a] transition-colors cursor-pointer">
                          {finding.title}
                        </h3>
                        <p className="text-sm text-white/50 mb-3">{finding.description}</p>

                        <div className="flex flex-wrap items-center gap-4 text-xs text-white/40">
                          <div className="flex items-center gap-1">
                            <GitBranch className="w-3 h-3" />
                            <span className="font-mono">{finding.repo}</span>
                          </div>
                          <div className="flex items-center gap-1">
                            <Code className="w-3 h-3" />
                            <span className="font-mono">{finding.file}:{finding.line}</span>
                          </div>
                          <div className="flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            <span>{finding.discoveredAt}</span>
                          </div>
                        </div>
                      </div>

                      {/* Actions */}
                      <div className="flex items-center gap-2">
                        <motion.button
                          whileHover={{ scale: 1.05 }}
                          whileTap={{ scale: 0.95 }}
                          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[#5c1a28]/30 border border-[#5c1a28]/40 text-[#8b3a4a] text-sm font-medium hover:bg-[#5c1a28]/40 transition-all"
                        >
                          <Shield className="w-4 h-4" />
                          Remediate
                        </motion.button>
                        <motion.button
                          whileHover={{ scale: 1.05 }}
                          whileTap={{ scale: 0.95 }}
                          className="p-2 rounded-lg bg-white/5 border border-white/10 text-white/50 hover:text-white hover:bg-white/10 transition-all"
                        >
                          <ChevronRight className="w-5 h-5" />
                        </motion.button>
                      </div>
                    </div>
                  </div>
                </GlassCard>
              </motion.div>
            )
          })}
        </div>
      </main>
    </div>
  )
}
