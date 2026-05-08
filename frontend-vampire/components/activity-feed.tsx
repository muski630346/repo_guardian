'use client'

import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Terminal,
  AlertTriangle,
  Check,
  Clock,
  Zap,
} from 'lucide-react'

import { GlassCard } from './glass-card'
import { cn } from '@/lib/utils'

const statusConfig = {
  success: {
    icon: Check,
    color: 'text-emerald-400',
    bg: 'bg-emerald-400/10',
    border: 'border-emerald-400/30',
  },

  warning: {
    icon: AlertTriangle,
    color: 'text-red-400',
    bg: 'bg-red-500/10',
    border: 'border-red-500/30',
  },

  info: {
    icon: Zap,
    color: 'text-[#8b3a4a]',
    bg: 'bg-[#5c1a28]/20',
    border: 'border-[#5c1a28]/30',
  },
}

export function ActivityFeed() {
  const [activities, setActivities] = useState<any[]>([])

  useEffect(() => {
    async function fetchActivities() {
      try {
        const response = await fetch(
          'http://127.0.0.1:8000/activity-feed'
        )

        const data = await response.json()

        console.log('Activity Feed:', data)

        setActivities(data.activities || [])
      } catch (error) {
        console.error('Activity Feed Error:', error)
      }
    }

    fetchActivities()

    const interval = setInterval(fetchActivities, 4000)

    return () => clearInterval(interval)
  }, [])

  return (
    <GlassCard delay={0.6}>
      <div className="p-6 lg:p-8">
        {/* HEADER */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-bold text-white flex items-center gap-3">
              <Terminal className="w-6 h-6 text-[#8b3a4a]" />
              Live Security Feed
            </h2>

            <p className="text-white/40 text-sm mt-1">
              Real-time autonomous AI operations
            </p>
          </div>

          <div className="flex items-center gap-2">
            <motion.div
              animate={{ opacity: [1, 0.3, 1] }}
              transition={{
                duration: 1,
                repeat: Infinity,
              }}
              className="w-2 h-2 bg-red-500 rounded-full"
            />

            <span className="text-xs font-mono text-red-400">
              LIVE
            </span>
          </div>
        </div>

        {/* TERMINAL */}
        <div className="bg-black/80 rounded-2xl border border-white/10 overflow-hidden backdrop-blur-xl">
          {/* TERMINAL TOP */}
          <div className="flex items-center gap-2 px-4 py-3 border-b border-white/10 bg-[#120005]">
            <div className="w-3 h-3 rounded-full bg-red-500" />
            <div className="w-3 h-3 rounded-full bg-yellow-500" />
            <div className="w-3 h-3 rounded-full bg-green-500" />

            <span className="ml-4 text-xs text-white/30 font-mono">
              repoguardian@live-security-feed
            </span>
          </div>

          {/* FEED */}
          <div className="h-[420px] overflow-y-auto p-4 space-y-3">
            <AnimatePresence>
              {activities.map((activity, index) => {
                const config =
                  statusConfig[
                    activity.level as keyof typeof statusConfig
                  ] || statusConfig.info

                const Icon = config.icon

                return (
                  <motion.div
                    key={index}
                    initial={{
                      opacity: 0,
                      x: -20,
                    }}
                    animate={{
                      opacity: 1,
                      x: 0,
                    }}
                    exit={{
                      opacity: 0,
                    }}
                    transition={{
                      duration: 0.35,
                    }}
                    className={cn(
                      'p-4 rounded-xl border flex items-start gap-4',
                      config.bg,
                      config.border
                    )}
                  >
                    <div
                      className={cn(
                        'mt-1',
                        config.color
                      )}
                    >
                      <Icon className="w-4 h-4" />
                    </div>

                    <div className="flex-1">
                      <p className="text-white/90 text-sm font-mono leading-relaxed">
                        {activity.message}
                      </p>
                    </div>

                    <div className="flex items-center gap-1 text-white/30">
                      <Clock className="w-3 h-3" />

                      <span className="text-xs font-mono">
                        {activity.timestamp}
                      </span>
                    </div>
                  </motion.div>
                )
              })}
            </AnimatePresence>

            {/* CURSOR */}
            <motion.div
              animate={{
                opacity: [1, 0, 1],
              }}
              transition={{
                duration: 1,
                repeat: Infinity,
              }}
              className="flex items-center gap-2 text-[#8b3a4a] font-mono text-sm"
            >
              <span>{'>'}</span>

              <span className="w-2 h-4 bg-[#8b0000]" />
            </motion.div>
          </div>
        </div>

        {/* FOOTER STATS */}
        <div className="grid grid-cols-3 gap-4 mt-6">
          {[
            {
              label: 'Events/min',
              value: activities.length * 6,
            },

            {
              label: 'Active Agents',
              value: '4',
            },

            {
              label: 'Threat Level',
              value: 'HIGH',
            },
          ].map((stat, i) => (
            <motion.div
              key={stat.label}
              initial={{
                opacity: 0,
                y: 10,
              }}
              animate={{
                opacity: 1,
                y: 0,
              }}
              transition={{
                delay: 0.2 + i * 0.1,
              }}
              className="bg-[#120005]/70 border border-white/10 rounded-xl p-4 text-center"
            >
              <p className="text-2xl font-bold text-white">
                {stat.value}
              </p>

              <p className="text-xs text-white/40 mt-1">
                {stat.label}
              </p>
            </motion.div>
          ))}
        </div>
      </div>
    </GlassCard>
  )
}