'use client'

import { motion } from 'framer-motion'
import { 
  GitPullRequest, 
  GitMerge, 
  Shield, 
  Check, 
  X, 
  Clock,
  User,
  MessageSquare,
  Eye
} from 'lucide-react'
import { AnimatedBackground } from '@/components/animated-background'
import { Navbar } from '@/components/navbar'
import { GlassCard } from '@/components/glass-card'
import { cn } from '@/lib/utils'

const pullRequests = [
  {
    id: 1,
    title: 'feat: Add OAuth2 authentication flow',
    repo: 'api-gateway',
    author: 'Sarah Chen',
    avatar: 'SC',
    status: 'approved',
    securityScore: 98,
    mergeConfidence: 95,
    comments: 12,
    reviewers: 3,
    additions: 847,
    deletions: 234,
    createdAt: '2 hours ago',
    branch: 'feature/oauth2-auth',
  },
  {
    id: 2,
    title: 'fix: Patch SQL injection vulnerability in user service',
    repo: 'backend-core',
    author: 'Alex Kim',
    avatar: 'AK',
    status: 'pending',
    securityScore: 75,
    mergeConfidence: 82,
    comments: 8,
    reviewers: 2,
    additions: 156,
    deletions: 89,
    createdAt: '4 hours ago',
    branch: 'hotfix/sql-injection',
  },
  {
    id: 3,
    title: 'refactor: Migrate to TypeScript strict mode',
    repo: 'web-frontend',
    author: 'Jordan Lee',
    avatar: 'JL',
    status: 'changes_requested',
    securityScore: 88,
    mergeConfidence: 60,
    comments: 24,
    reviewers: 4,
    additions: 2341,
    deletions: 1876,
    createdAt: '1 day ago',
    branch: 'refactor/typescript-strict',
  },
  {
    id: 4,
    title: 'chore: Update dependencies to latest versions',
    repo: 'infrastructure',
    author: 'Morgan Swift',
    avatar: 'MS',
    status: 'approved',
    securityScore: 100,
    mergeConfidence: 99,
    comments: 3,
    reviewers: 2,
    additions: 234,
    deletions: 198,
    createdAt: '3 hours ago',
    branch: 'chore/dep-updates',
  },
  {
    id: 5,
    title: 'feat: Implement rate limiting middleware',
    repo: 'api-gateway',
    author: 'Casey Rivera',
    avatar: 'CR',
    status: 'pending',
    securityScore: 92,
    mergeConfidence: 88,
    comments: 15,
    reviewers: 3,
    additions: 523,
    deletions: 67,
    createdAt: '6 hours ago',
    branch: 'feature/rate-limiting',
  },
]

const statusConfig = {
  approved: {
    label: 'Approved',
    color: 'text-emerald-400',
    bg: 'bg-emerald-500/20',
    border: 'border-emerald-500/30',
    icon: Check,
  },
  pending: {
    label: 'Pending Review',
    color: 'text-yellow-400',
    bg: 'bg-yellow-500/20',
    border: 'border-yellow-500/30',
    icon: Clock,
  },
  changes_requested: {
    label: 'Changes Requested',
    color: 'text-red-400',
    bg: 'bg-red-500/20',
    border: 'border-red-500/30',
    icon: X,
  },
}

function SecurityScoreRing({ score }: { score: number }) {
  const circumference = 2 * Math.PI * 40
  const offset = circumference - (score / 100) * circumference
  const color = score >= 90 ? '#10b981' : score >= 70 ? '#f59e0b' : '#ef4444'

  return (
    <div className="relative w-24 h-24">
      <svg className="w-full h-full transform -rotate-90">
        <circle
          cx="48"
          cy="48"
          r="40"
          fill="none"
          stroke="rgba(255,255,255,0.1)"
          strokeWidth="8"
        />
        <motion.circle
          cx="48"
          cy="48"
          r="40"
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1, ease: 'easeOut' }}
          strokeLinecap="round"
          style={{ filter: `drop-shadow(0 0 6px ${color})` }}
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center flex-col">
        <span className="text-xl font-bold text-white">{score}</span>
        <span className="text-[10px] text-white/50 uppercase tracking-wider">Security</span>
      </div>
    </div>
  )
}

export default function PRFeedPage() {
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
            Pull Request <span className="text-[#8b3a4a] text-glow">Intelligence</span>
          </h1>
          <p className="text-white/50 text-lg max-w-2xl">
            AI-powered security analysis for every code change. 
            Automated review insights and merge confidence scoring.
          </p>
        </motion.div>

        {/* Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 lg:gap-6 mb-8 lg:mb-12">
          {[
            { label: 'Open PRs', value: '23', change: '+5 today' },
            { label: 'Avg Security Score', value: '91%', change: '+3% this week' },
            { label: 'Auto-Approved', value: '67%', change: 'of safe PRs' },
            { label: 'Blocked', value: '3', change: 'security issues' },
          ].map((stat, i) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
            >
              <GlassCard delay={i * 0.1}>
                <div className="p-4 lg:p-6">
                  <p className="text-2xl lg:text-3xl font-bold text-white">{stat.value}</p>
                  <p className="text-sm text-white/50 mt-1">{stat.label}</p>
                  <p className="text-xs text-[#8b3a4a] mt-2">{stat.change}</p>
                </div>
              </GlassCard>
            </motion.div>
          ))}
        </div>

        {/* PR List */}
        <div className="space-y-4 lg:space-y-6">
          {pullRequests.map((pr, i) => {
            const status = statusConfig[pr.status as keyof typeof statusConfig]
            const StatusIcon = status.icon

            return (
              <motion.div
                key={pr.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.2 + i * 0.1 }}
              >
                <GlassCard delay={0.2 + i * 0.1}>
                  <div className="p-4 lg:p-6">
                    <div className="flex flex-col lg:flex-row lg:items-center gap-4 lg:gap-6">
                      {/* Security Score Ring */}
                      <div className="hidden lg:block">
                        <SecurityScoreRing score={pr.securityScore} />
                      </div>

                      {/* PR Info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-4 mb-3">
                          <div>
                            <div className="flex items-center gap-2 mb-2">
                              <GitPullRequest className="w-4 h-4 text-[#8b3a4a]" />
                              <span className="text-xs font-mono text-white/40">{pr.repo}</span>
                              <span className="text-xs text-white/20">/</span>
                              <span className="text-xs font-mono text-white/40">{pr.branch}</span>
                            </div>
                            <h3 className="text-lg font-semibold text-white hover:text-[#8b3a4a] transition-colors cursor-pointer">
                              {pr.title}
                            </h3>
                          </div>
                          <div className={cn(
                            'flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold',
                            status.bg,
                            status.border,
                            status.color,
                            'border'
                          )}>
                            <StatusIcon className="w-3 h-3" />
                            {status.label}
                          </div>
                        </div>

                        {/* Author & Meta */}
                        <div className="flex flex-wrap items-center gap-4 text-sm text-white/50">
                          <div className="flex items-center gap-2">
                            <div className="w-6 h-6 rounded-full bg-gradient-to-br from-[#5c1a28] to-[#3d1018] flex items-center justify-center text-[10px] font-bold text-white">
                              {pr.avatar}
                            </div>
                            <span>{pr.author}</span>
                          </div>
                          <div className="flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            <span>{pr.createdAt}</span>
                          </div>
                          <div className="flex items-center gap-1">
                            <MessageSquare className="w-3 h-3" />
                            <span>{pr.comments}</span>
                          </div>
                          <div className="flex items-center gap-1">
                            <Eye className="w-3 h-3" />
                            <span>{pr.reviewers} reviewers</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-emerald-400">+{pr.additions}</span>
                            <span className="text-red-400">-{pr.deletions}</span>
                          </div>
                        </div>

                        {/* Mobile Security Score */}
                        <div className="lg:hidden mt-4 flex items-center gap-4">
                          <div className="flex items-center gap-2">
                            <Shield className="w-4 h-4 text-[#8b3a4a]" />
                            <span className="text-sm text-white/70">Security: <span className="text-white font-semibold">{pr.securityScore}%</span></span>
                          </div>
                          <div className="flex items-center gap-2">
                            <GitMerge className="w-4 h-4 text-emerald-400" />
                            <span className="text-sm text-white/70">Merge: <span className="text-white font-semibold">{pr.mergeConfidence}%</span></span>
                          </div>
                        </div>
                      </div>

                      {/* Merge Confidence & Actions */}
                      <div className="flex lg:flex-col items-center gap-3 lg:gap-4">
                        <div className="hidden lg:block text-center">
                          <p className="text-2xl font-bold text-white">{pr.mergeConfidence}%</p>
                          <p className="text-xs text-white/40">Merge Confidence</p>
                        </div>
                        <motion.button
                          whileHover={{ scale: 1.02 }}
                          whileTap={{ scale: 0.98 }}
                          disabled={pr.status !== 'approved'}
                          className={cn(
                            'flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-sm transition-all',
                            pr.status === 'approved'
                              ? 'bg-gradient-to-r from-emerald-600 to-emerald-700 text-white hover:shadow-[0_0_20px_rgba(16,185,129,0.3)]'
                              : 'bg-white/5 text-white/30 cursor-not-allowed'
                          )}
                        >
                          <GitMerge className="w-4 h-4" />
                          Merge
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
