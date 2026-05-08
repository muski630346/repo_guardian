'use client'

import { motion } from 'framer-motion'
import { LucideIcon } from 'lucide-react'
import { GlassCard } from './glass-card'
import { cn } from '@/lib/utils'

interface MetricCardProps {
  title: string
  value: string | number
  change?: number
  changeLabel?: string
  icon: LucideIcon
  color?: 'red' | 'green' | 'blue' | 'white'
  delay?: number
  chart?: React.ReactNode
}

export function MetricCard({
  title,
  value,
  change,
  changeLabel,
  icon: Icon,
  color = 'red',
  delay = 0,
  chart,
}: MetricCardProps) {
  const colorClasses = {
    red: 'from-[#5c1a28] to-[#3d1018]',
    green: 'from-emerald-500 to-emerald-700',
    blue: 'from-blue-500 to-blue-700',
    white: 'from-white/20 to-white/10',
  }

  const glowClasses = {
    red: 'bg-[#5c1a28]',
    green: 'bg-emerald-500',
    blue: 'bg-blue-500',
    white: 'bg-white',
  }

  return (
    <GlassCard delay={delay} className="h-full">
      <div className="p-5 lg:p-6 h-full flex flex-col">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            <motion.div
              className="relative"
              animate={{ scale: [1, 1.1, 1] }}
              transition={{ duration: 2, repeat: Infinity }}
            >
              <div className={cn('absolute inset-0 blur-xl opacity-50', glowClasses[color])} />
              <div className={cn(
                'relative w-10 h-10 lg:w-12 lg:h-12 rounded-xl bg-gradient-to-br flex items-center justify-center',
                colorClasses[color]
              )}>
                <Icon className="w-5 h-5 lg:w-6 lg:h-6 text-white" />
              </div>
            </motion.div>
            <div>
              <p className="text-xs lg:text-sm text-white/50 font-medium uppercase tracking-wider">
                {title}
              </p>
            </div>
          </div>
          
          {change !== undefined && (
            <motion.div
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: delay + 0.3 }}
              className={cn(
                'flex items-center gap-1 px-2 py-1 rounded-full text-xs font-mono',
                change >= 0 
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' 
                  : 'bg-red-500/20 text-red-400 border border-red-500/30'
              )}
            >
              {change >= 0 ? '↑' : '↓'} {Math.abs(change)}%
            </motion.div>
          )}
        </div>

        {/* Value */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: delay + 0.2 }}
          className="flex-1"
        >
          <h3 className="text-3xl lg:text-4xl font-bold text-white tracking-tight text-glow-white">
            {value}
          </h3>
          {changeLabel && (
            <p className="text-xs lg:text-sm text-white/40 mt-1">{changeLabel}</p>
          )}
        </motion.div>

        {/* Chart */}
        {chart && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: delay + 0.4 }}
            className="mt-4 h-16"
          >
            {chart}
          </motion.div>
        )}

        {/* Bottom glow line */}
        <motion.div
          className={cn('h-0.5 rounded-full mt-4', `bg-gradient-to-r ${colorClasses[color]}`)}
          initial={{ scaleX: 0 }}
          animate={{ scaleX: 1 }}
          transition={{ delay: delay + 0.5, duration: 0.8 }}
          style={{ transformOrigin: 'left' }}
        />
      </div>
    </GlassCard>
  )
}
