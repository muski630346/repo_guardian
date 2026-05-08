'use client'

import { motion } from 'framer-motion'

export function AnimatedBackground() {
  return (
    <div className="fixed inset-0 overflow-hidden pointer-events-none">
      {/* Base Background */}
      <div className="absolute inset-0 bg-[#050505]" />

      {/* Red Ambient Glow */}
      <div className="absolute top-0 left-0 w-[600px] h-[600px] bg-red-900/20 blur-[140px]" />

      <div className="absolute bottom-0 right-0 w-[500px] h-[500px] bg-[#5c1a28]/20 blur-[140px]" />

      {/* Grid */}
      <div
        className="absolute inset-0 opacity-[0.06]"
        style={{
          backgroundImage: `
            linear-gradient(to right, white 1px, transparent 1px),
            linear-gradient(to bottom, white 1px, transparent 1px)
          `,
          backgroundSize: '80px 80px',
        }}
      />

      {/* Floating Glow Orbs */}
      <motion.div
        animate={{
          y: [0, -20, 0],
        }}
        transition={{
          duration: 6,
          repeat: Infinity,
        }}
        className="absolute top-[20%] left-[15%] w-40 h-40 rounded-full bg-red-700/10 blur-3xl"
      />

      <motion.div
        animate={{
          y: [0, 30, 0],
        }}
        transition={{
          duration: 8,
          repeat: Infinity,
        }}
        className="absolute bottom-[20%] right-[10%] w-52 h-52 rounded-full bg-[#8b3a4a]/10 blur-3xl"
      />
    </div>
  )
}