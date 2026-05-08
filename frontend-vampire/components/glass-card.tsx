'use client'

import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'

interface GlassCardProps {
  children: React.ReactNode
  className?: string
  glowColor?: 'red' | 'white' | 'none'
  hover?: boolean
  delay?: number
}

export function GlassCard({
  children,
  className,
  glowColor = 'red',
  hover = true,
  delay = 0,
}: GlassCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      whileHover={hover ? { y: -5, scale: 1.01 } : undefined}
      className={cn(
        'relative group rounded-xl overflow-hidden',
        className
      )}
    >
      {/* Glass background */}
      <div className="absolute inset-0 bg-gradient-to-br from-[#2d0a12]/60 to-[#050505]/80 backdrop-blur-xl" />
      
      {/* Animated border */}
      <div
        className={cn(
          'absolute inset-0 rounded-xl transition-all duration-500',
          glowColor === 'red' && 'border border-[#5c1a28]/30 group-hover:border-[#5c1a28]/60 group-hover:shadow-[0_0_30px_rgba(92,26,40,0.4)]',
          glowColor === 'white' && 'border border-white/10 group-hover:border-white/30 group-hover:shadow-[0_0_30px_rgba(255,255,255,0.1)]',
          glowColor === 'none' && 'border border-white/5'
        )}
      />
      
      {/* Holographic shine effect */}
      <motion.div
        className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500"
        style={{
          background: 'linear-gradient(105deg, transparent 40%, rgba(92, 26, 40, 0.15) 45%, rgba(92, 26, 40, 0.2) 50%, rgba(92, 26, 40, 0.15) 55%, transparent 60%)',
        }}
        animate={{
          x: ['-100%', '200%'],
        }}
        transition={{
          duration: 2,
          repeat: Infinity,
          repeatDelay: 3,
        }}
      />
      
      {/* Corner accents */}
      <div className="absolute top-0 left-0 w-8 h-8 border-l-2 border-t-2 border-[#5c1a28]/40 rounded-tl-xl" />
      <div className="absolute top-0 right-0 w-8 h-8 border-r-2 border-t-2 border-[#5c1a28]/40 rounded-tr-xl" />
      <div className="absolute bottom-0 left-0 w-8 h-8 border-l-2 border-b-2 border-[#5c1a28]/40 rounded-bl-xl" />
      <div className="absolute bottom-0 right-0 w-8 h-8 border-r-2 border-b-2 border-[#5c1a28]/40 rounded-br-xl" />
      
      {/* Content */}
      <div className="relative z-10">{children}</div>
    </motion.div>
  )
}
