'use client'

import { motion } from 'framer-motion'
import { 
  FileBarChart, 
  Download, 
  Calendar,
  TrendingUp,
  Shield,
  AlertTriangle,
  Clock,
  ArrowUpRight,
  ArrowDownRight
} from 'lucide-react'
import { AnimatedBackground } from '@/components/animated-background'
import { Navbar } from '@/components/navbar'
import { GlassCard } from '@/components/glass-card'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
} from 'recharts'

const trendData = [
  { month: 'Jan', vulnerabilities: 45, remediated: 38, score: 78 },
  { month: 'Feb', vulnerabilities: 52, remediated: 48, score: 82 },
  { month: 'Mar', vulnerabilities: 38, remediated: 35, score: 85 },
  { month: 'Apr', vulnerabilities: 29, remediated: 28, score: 89 },
  { month: 'May', vulnerabilities: 18, remediated: 17, score: 93 },
  { month: 'Jun', vulnerabilities: 12, remediated: 11, score: 96 },
]

const severityData = [
  { name: 'Critical', value: 3, color: '#ef4444' },
  { name: 'High', value: 8, color: '#f97316' },
  { name: 'Medium', value: 15, color: '#eab308' },
  { name: 'Low', value: 24, color: '#3b82f6' },
]

const categoryData = [
  { category: 'Injection', count: 12 },
  { category: 'XSS', count: 8 },
  { category: 'Secrets', count: 6 },
  { category: 'AuthZ', count: 10 },
  { category: 'Config', count: 7 },
  { category: 'Crypto', count: 4 },
]

const recentReports = [
  {
    id: 1,
    title: 'Q2 2024 Security Assessment',
    type: 'Quarterly Report',
    date: 'Jun 30, 2024',
    status: 'completed',
    findings: 23,
    pages: 48,
  },
  {
    id: 2,
    title: 'SOC 2 Type II Compliance',
    type: 'Compliance Report',
    date: 'Jun 15, 2024',
    status: 'completed',
    findings: 0,
    pages: 124,
  },
  {
    id: 3,
    title: 'Penetration Test Results',
    type: 'Security Audit',
    date: 'Jun 1, 2024',
    status: 'completed',
    findings: 7,
    pages: 36,
  },
  {
    id: 4,
    title: 'Weekly Vulnerability Scan',
    type: 'Automated Report',
    date: 'Jul 7, 2024',
    status: 'in_progress',
    findings: 5,
    pages: 12,
  },
]

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-[#0a0000]/95 border border-[#5c1a28]/40 rounded-lg p-3 backdrop-blur-xl">
        <p className="text-white font-medium mb-2">{label}</p>
        {payload.map((entry: any, index: number) => (
          <p key={index} className="text-sm" style={{ color: entry.color }}>
            {entry.name}: {entry.value}
          </p>
        ))}
      </div>
    )
  }
  return null
}

export default function ReportsPage() {
  return (
    <div className="min-h-screen bg-[#050505] text-white">
      <AnimatedBackground />
      <Navbar />
      
      <main className="relative pt-24 lg:pt-28 pb-12 px-4 lg:px-8 max-w-[1800px] mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 mb-8 lg:mb-12"
        >
          <div>
            <h1 className="text-3xl lg:text-5xl font-bold text-white mb-3">
              Security <span className="text-[#8b3a4a] text-glow">Reports</span>
            </h1>
            <p className="text-white/50 text-lg max-w-2xl">
              Comprehensive security analytics and compliance documentation.
              Export detailed reports for stakeholders and auditors.
            </p>
          </div>
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className="flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-[#5c1a28] to-[#3d1018] text-white font-semibold"
          >
            <Download className="w-5 h-5" />
            Export Report
          </motion.button>
        </motion.div>

        {/* Quick Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 lg:gap-6 mb-8 lg:mb-12">
          {[
            { label: 'Security Score', value: '96%', change: '+8%', positive: true, icon: Shield },
            { label: 'Open Findings', value: '7', change: '-45%', positive: true, icon: AlertTriangle },
            { label: 'Avg Resolution', value: '4.2h', change: '-2.1h', positive: true, icon: Clock },
            { label: 'Scans This Week', value: '847', change: '+12%', positive: true, icon: TrendingUp },
          ].map((stat, i) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
            >
              <GlassCard delay={i * 0.1}>
                <div className="p-4 lg:p-6">
                  <div className="flex items-start justify-between mb-2">
                    <stat.icon className="w-5 h-5 text-[#8b3a4a]" />
                    <div className={`flex items-center gap-1 text-xs font-medium ${
                      stat.positive ? 'text-emerald-400' : 'text-red-400'
                    }`}>
                      {stat.positive ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                      {stat.change}
                    </div>
                  </div>
                  <p className="text-2xl lg:text-3xl font-bold text-white">{stat.value}</p>
                  <p className="text-sm text-white/50 mt-1">{stat.label}</p>
                </div>
              </GlassCard>
            </motion.div>
          ))}
        </div>

        {/* Charts Row */}
        <div className="grid lg:grid-cols-2 gap-6 lg:gap-8 mb-8 lg:mb-12">
          {/* Trend Chart */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <GlassCard delay={0.2}>
              <div className="p-6">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-[#8b3a4a]" />
                  Vulnerability Trend
                </h3>
                <div className="h-[280px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={trendData}>
                      <defs>
                        <linearGradient id="vulnGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#5c1a28" stopOpacity={0.5} />
                          <stop offset="100%" stopColor="#5c1a28" stopOpacity={0} />
                        </linearGradient>
                        <linearGradient id="remGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#10b981" stopOpacity={0.4} />
                          <stop offset="100%" stopColor="#10b981" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                      <XAxis dataKey="month" stroke="rgba(255,255,255,0.3)" fontSize={12} />
                      <YAxis stroke="rgba(255,255,255,0.3)" fontSize={12} />
                      <Tooltip content={<CustomTooltip />} />
                      <Area
                        type="monotone"
                        dataKey="vulnerabilities"
                        name="Detected"
                        stroke="#5c1a28"
                        fill="url(#vulnGradient)"
                        strokeWidth={2}
                      />
                      <Area
                        type="monotone"
                        dataKey="remediated"
                        name="Remediated"
                        stroke="#10b981"
                        fill="url(#remGradient)"
                        strokeWidth={2}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </GlassCard>
          </motion.div>

          {/* Severity Distribution */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
          >
            <GlassCard delay={0.3}>
              <div className="p-6">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                  <AlertTriangle className="w-5 h-5 text-[#8b3a4a]" />
                  Severity Distribution
                </h3>
                <div className="flex items-center gap-6">
                  <div className="h-[200px] w-[200px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={severityData}
                          cx="50%"
                          cy="50%"
                          innerRadius={60}
                          outerRadius={90}
                          paddingAngle={4}
                          dataKey="value"
                        >
                          {severityData.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.color} />
                          ))}
                        </Pie>
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="flex-1 space-y-3">
                    {severityData.map((item) => (
                      <div key={item.name} className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <div className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }} />
                          <span className="text-sm text-white/70">{item.name}</span>
                        </div>
                        <span className="text-sm font-semibold text-white">{item.value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </GlassCard>
          </motion.div>
        </div>

        {/* Category Breakdown */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="mb-8 lg:mb-12"
        >
          <GlassCard delay={0.4}>
            <div className="p-6">
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <FileBarChart className="w-5 h-5 text-[#8b3a4a]" />
                Findings by Category
              </h3>
              <div className="h-[200px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={categoryData} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                    <XAxis type="number" stroke="rgba(255,255,255,0.3)" fontSize={12} />
                    <YAxis dataKey="category" type="category" stroke="rgba(255,255,255,0.3)" fontSize={12} width={80} />
                    <Tooltip content={<CustomTooltip />} />
                    <Bar dataKey="count" fill="#5c1a28" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </GlassCard>
        </motion.div>

        {/* Recent Reports */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
        >
          <GlassCard delay={0.5}>
            <div className="p-6">
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <Calendar className="w-5 h-5 text-[#8b3a4a]" />
                Recent Reports
              </h3>
              <div className="space-y-3">
                {recentReports.map((report, i) => (
                  <motion.div
                    key={report.id}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.6 + i * 0.1 }}
                    className="flex flex-col sm:flex-row sm:items-center justify-between p-4 rounded-xl bg-white/5 border border-white/5 hover:border-[#5c1a28]/40 transition-all cursor-pointer group"
                  >
                    <div className="flex items-center gap-4 mb-2 sm:mb-0">
                      <div className="w-10 h-10 rounded-lg bg-[#5c1a28]/30 flex items-center justify-center">
                        <FileBarChart className="w-5 h-5 text-[#8b3a4a]" />
                      </div>
                      <div>
                        <h4 className="text-sm font-semibold text-white group-hover:text-[#8b3a4a] transition-colors">
                          {report.title}
                        </h4>
                        <p className="text-xs text-white/40">{report.type} • {report.date}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <p className="text-sm text-white/70">{report.findings} findings</p>
                        <p className="text-xs text-white/40">{report.pages} pages</p>
                      </div>
                      <motion.button
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        className="p-2 rounded-lg bg-white/5 border border-white/10 text-white/50 hover:text-white hover:bg-white/10 transition-all"
                      >
                        <Download className="w-4 h-4" />
                      </motion.button>
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>
          </GlassCard>
        </motion.div>
      </main>
    </div>
  )
}
