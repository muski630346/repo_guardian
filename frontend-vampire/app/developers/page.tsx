'use client'

import { motion } from 'framer-motion'
import { 
  Users, 
  Shield, 
  GitCommit, 
  Award,
  TrendingUp,
  AlertTriangle,
  Check,
  Star
} from 'lucide-react'
import { AnimatedBackground } from '@/components/animated-background'
import { Navbar } from '@/components/navbar'
import { GlassCard } from '@/components/glass-card'
import { cn } from '@/lib/utils'

const developers = [
  {
    id: 1,
    name: 'Sarah Chen',
    avatar: 'SC',
    role: 'Senior Security Engineer',
    team: 'Platform Security',
    trustScore: 98,
    reputation: 'Excellent',
    commits: 1247,
    prsReviewed: 342,
    vulnerabilitiesFixed: 89,
    secureCodeRatio: 99.2,
    avgReviewTime: '2.4h',
    badges: ['Security Champion', 'Top Contributor', 'Zero Vulnerabilities'],
    activityData: [65, 72, 80, 75, 85, 90, 88, 92, 95, 98],
  },
  {
    id: 2,
    name: 'Alex Kim',
    avatar: 'AK',
    role: 'Full Stack Developer',
    team: 'Core Engineering',
    trustScore: 92,
    reputation: 'Very Good',
    commits: 856,
    prsReviewed: 189,
    vulnerabilitiesFixed: 34,
    secureCodeRatio: 96.8,
    avgReviewTime: '4.1h',
    badges: ['Fast Reviewer', 'Code Quality'],
    activityData: [50, 55, 60, 58, 65, 70, 72, 75, 80, 85],
  },
  {
    id: 3,
    name: 'Jordan Lee',
    avatar: 'JL',
    role: 'DevOps Engineer',
    team: 'Infrastructure',
    trustScore: 95,
    reputation: 'Excellent',
    commits: 634,
    prsReviewed: 278,
    vulnerabilitiesFixed: 56,
    secureCodeRatio: 98.1,
    avgReviewTime: '1.8h',
    badges: ['Infrastructure Guardian', 'Quick Response'],
    activityData: [70, 75, 72, 78, 82, 85, 88, 90, 92, 95],
  },
  {
    id: 4,
    name: 'Morgan Swift',
    avatar: 'MS',
    role: 'Backend Developer',
    team: 'API Gateway',
    trustScore: 78,
    reputation: 'Good',
    commits: 423,
    prsReviewed: 98,
    vulnerabilitiesFixed: 12,
    secureCodeRatio: 89.4,
    avgReviewTime: '6.2h',
    badges: ['Rising Star'],
    activityData: [40, 45, 50, 55, 60, 58, 62, 68, 72, 78],
  },
  {
    id: 5,
    name: 'Casey Rivera',
    avatar: 'CR',
    role: 'Frontend Developer',
    team: 'Web Platform',
    trustScore: 88,
    reputation: 'Very Good',
    commits: 712,
    prsReviewed: 156,
    vulnerabilitiesFixed: 28,
    secureCodeRatio: 94.6,
    avgReviewTime: '3.5h',
    badges: ['UI Security Expert', 'Accessibility Champion'],
    activityData: [55, 60, 65, 70, 72, 75, 80, 82, 85, 88],
  },
]

function TrustScoreRing({ score }: { score: number }) {
  const circumference = 2 * Math.PI * 45
  const offset = circumference - (score / 100) * circumference
  const color = score >= 95 ? '#10b981' : score >= 80 ? '#f59e0b' : score >= 60 ? '#f97316' : '#ef4444'

  return (
    <div className="relative w-28 h-28">
      <svg className="w-full h-full transform -rotate-90">
        <circle
          cx="56"
          cy="56"
          r="45"
          fill="none"
          stroke="rgba(255,255,255,0.05)"
          strokeWidth="10"
        />
        <motion.circle
          cx="56"
          cy="56"
          r="45"
          fill="none"
          stroke={color}
          strokeWidth="10"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1.5, ease: 'easeOut' }}
          strokeLinecap="round"
          style={{ filter: `drop-shadow(0 0 8px ${color})` }}
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center flex-col">
        <span className="text-2xl font-bold text-white">{score}</span>
        <span className="text-[10px] text-white/40 uppercase tracking-wider">Trust</span>
      </div>
    </div>
  )
}

function MiniActivityChart({ data }: { data: number[] }) {
  const max = Math.max(...data)
  
  return (
    <div className="flex items-end gap-1 h-12">
      {data.map((value, i) => (
        <motion.div
          key={i}
          initial={{ height: 0 }}
          animate={{ height: `${(value / max) * 100}%` }}
          transition={{ delay: i * 0.05, duration: 0.3 }}
          className="w-2 bg-gradient-to-t from-[#5c1a28]/60 to-[#5c1a28] rounded-t"
        />
      ))}
    </div>
  )
}

export default function DevelopersPage() {
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
            Developer <span className="text-[#8b3a4a] text-glow">Intelligence</span>
          </h1>
          <p className="text-white/50 text-lg max-w-2xl">
            AI-powered developer reputation and security performance tracking.
            Trust scores based on code quality and security practices.
          </p>
        </motion.div>

        {/* Team Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 lg:gap-6 mb-8 lg:mb-12">
          {[
            { label: 'Total Developers', value: '47', icon: Users, change: '+5 this month' },
            { label: 'Avg Trust Score', value: '91', icon: Shield, change: '+3 points' },
            { label: 'Security Champions', value: '12', icon: Award, change: '25% of team' },
            { label: 'Vulnerabilities Fixed', value: '219', icon: Check, change: 'this quarter' },
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
                  </div>
                  <p className="text-2xl lg:text-3xl font-bold text-white">{stat.value}</p>
                  <p className="text-sm text-white/50 mt-1">{stat.label}</p>
                  <p className="text-xs text-[#8b3a4a] mt-2">{stat.change}</p>
                </div>
              </GlassCard>
            </motion.div>
          ))}
        </div>

        {/* Developers Grid */}
        <div className="grid lg:grid-cols-2 gap-4 lg:gap-6">
          {developers.map((dev, i) => (
            <motion.div
              key={dev.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 + i * 0.1 }}
            >
              <GlassCard delay={0.2 + i * 0.1}>
                <div className="p-4 lg:p-6">
                  <div className="flex flex-col sm:flex-row gap-4 lg:gap-6">
                    {/* Trust Score Ring */}
                    <div className="flex sm:block items-center gap-4">
                      <TrustScoreRing score={dev.trustScore} />
                      <div className="sm:hidden">
                        <h3 className="text-lg font-semibold text-white">{dev.name}</h3>
                        <p className="text-sm text-white/50">{dev.role}</p>
                      </div>
                    </div>

                    {/* Developer Info */}
                    <div className="flex-1">
                      {/* Header - Hidden on mobile */}
                      <div className="hidden sm:block mb-4">
                        <div className="flex items-center gap-3 mb-1">
                          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#5c1a28] to-[#3d1018] flex items-center justify-center text-sm font-bold text-white">
                            {dev.avatar}
                          </div>
                          <div>
                            <h3 className="text-lg font-semibold text-white">{dev.name}</h3>
                            <p className="text-sm text-white/50">{dev.role}</p>
                          </div>
                        </div>
                        <p className="text-xs text-white/40 mt-1">{dev.team}</p>
                      </div>

                      {/* Badges */}
                      <div className="flex flex-wrap gap-2 mb-4">
                        {dev.badges.map((badge) => (
                          <span
                            key={badge}
                            className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-[10px] font-medium bg-[#5c1a28]/20 border border-[#5c1a28]/30 text-[#8b3a4a]"
                          >
                            <Star className="w-3 h-3" />
                            {badge}
                          </span>
                        ))}
                      </div>

                      {/* Stats Grid */}
                      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
                        <div className="p-2 rounded-lg bg-white/5">
                          <p className="text-lg font-bold text-white">{dev.commits.toLocaleString()}</p>
                          <p className="text-[10px] text-white/40 uppercase">Commits</p>
                        </div>
                        <div className="p-2 rounded-lg bg-white/5">
                          <p className="text-lg font-bold text-white">{dev.prsReviewed}</p>
                          <p className="text-[10px] text-white/40 uppercase">PRs Reviewed</p>
                        </div>
                        <div className="p-2 rounded-lg bg-white/5">
                          <p className="text-lg font-bold text-emerald-400">{dev.vulnerabilitiesFixed}</p>
                          <p className="text-[10px] text-white/40 uppercase">Vulns Fixed</p>
                        </div>
                        <div className="p-2 rounded-lg bg-white/5">
                          <p className="text-lg font-bold text-white">{dev.secureCodeRatio}%</p>
                          <p className="text-[10px] text-white/40 uppercase">Secure Code</p>
                        </div>
                      </div>

                      {/* Activity Chart */}
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-xs text-white/40 mb-1">Activity (10 weeks)</p>
                          <MiniActivityChart data={dev.activityData} />
                        </div>
                        <div className="text-right">
                          <p className="text-xs text-white/40">Avg Review Time</p>
                          <p className="text-lg font-semibold text-white">{dev.avgReviewTime}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </GlassCard>
            </motion.div>
          ))}
        </div>
      </main>
    </div>
  )
}
