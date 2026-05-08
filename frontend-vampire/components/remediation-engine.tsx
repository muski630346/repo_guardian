'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Code, Sparkles, ArrowRight, Check, GitPullRequest, Shield } from 'lucide-react'
import { GlassCard } from './glass-card'

const vulnerableCode = `// Vulnerable: SQL Injection Risk
const getUserData = async (userId) => {
  const query = \`SELECT * FROM users 
    WHERE id = '\${userId}'\`;
  
  return await db.execute(query);
};`

const fixedCode = `// Fixed: Using Parameterized Queries
const getUserData = async (userId) => {
  const query = \`SELECT * FROM users 
    WHERE id = $1\`;
  
  return await db.execute(query, [userId]);
};`

export function RemediationEngine() {
  const [isRemediating, setIsRemediating] = useState(false)
  const [isComplete, setIsComplete] = useState(false)

  const handleRemediate = () => {
    setIsRemediating(true)
    setTimeout(() => {
      setIsRemediating(false)
      setIsComplete(true)
    }, 3000)
  }

  const handleReset = () => {
    setIsComplete(false)
  }

  return (
    <GlassCard delay={0.5}>
      <div className="p-6 lg:p-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <div>
            <h2 className="text-xl lg:text-2xl font-bold text-white flex items-center gap-3">
              <Sparkles className="w-6 h-6 text-[#8b3a4a]" />
              AI Remediation Engine
            </h2>
            <p className="text-white/50 text-sm mt-1">Intelligent code fixing with one click</p>
          </div>
          {isComplete && (
            <motion.button
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              onClick={handleReset}
              className="text-sm text-white/50 hover:text-white transition-colors"
            >
              Reset Demo
            </motion.button>
          )}
        </div>

        {/* Code Panels */}
        <div className="grid lg:grid-cols-2 gap-4 lg:gap-6">
          {/* Vulnerable Code */}
          <div className="relative">
            <div className="absolute top-3 left-3 flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-red-500" />
              <span className="text-xs font-mono text-red-400">VULNERABLE</span>
            </div>
            <motion.div
              className="bg-[#0a0000] rounded-xl border border-red-500/30 p-4 pt-10 overflow-hidden"
              animate={isRemediating ? { opacity: 0.5 } : { opacity: 1 }}
            >
              <pre className="text-sm font-mono text-white/80 overflow-x-auto">
                <code>{vulnerableCode}</code>
              </pre>
              
              {/* Scanning effect */}
              <AnimatePresence>
                {isRemediating && (
                  <motion.div
                    initial={{ top: 0 }}
                    animate={{ top: '100%' }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 2, repeat: Infinity }}
                    className="absolute left-0 right-0 h-1 bg-gradient-to-r from-transparent via-[#5c1a28] to-transparent"
                  />
                )}
              </AnimatePresence>
            </motion.div>
          </div>

          {/* Arrow / Process */}
          <div className="hidden lg:flex items-center justify-center absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-10">
            <AnimatePresence mode="wait">
              {isRemediating ? (
                <motion.div
                  key="loading"
                  initial={{ opacity: 0, scale: 0 }}
                  animate={{ opacity: 1, scale: 1, rotate: 360 }}
                  exit={{ opacity: 0, scale: 0 }}
                  transition={{ rotate: { duration: 1, repeat: Infinity, ease: 'linear' } }}
                  className="w-12 h-12 rounded-full border-2 border-[#5c1a28]/40 border-t-[#5c1a28]"
                />
              ) : isComplete ? (
                <motion.div
                  key="complete"
                  initial={{ opacity: 0, scale: 0 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="w-12 h-12 rounded-full bg-emerald-500/20 border border-emerald-500/50 flex items-center justify-center"
                >
                  <Check className="w-6 h-6 text-emerald-400" />
                </motion.div>
              ) : null}
            </AnimatePresence>
          </div>

          {/* Fixed Code */}
          <div className="relative">
            <div className="absolute top-3 left-3 flex items-center gap-2">
              <div className={`w-3 h-3 rounded-full transition-colors ${isComplete ? 'bg-emerald-500' : 'bg-white/20'}`} />
              <span className={`text-xs font-mono transition-colors ${isComplete ? 'text-emerald-400' : 'text-white/30'}`}>
                {isComplete ? 'SECURED' : 'AI FIX PREVIEW'}
              </span>
            </div>
            <motion.div
              className={`bg-[#000a00] rounded-xl border p-4 pt-10 overflow-hidden transition-all ${
                isComplete ? 'border-emerald-500/30' : 'border-white/10'
              }`}
              animate={isComplete ? { 
                boxShadow: '0 0 30px rgba(16, 185, 129, 0.2)' 
              } : {}}
            >
              <pre className={`text-sm font-mono overflow-x-auto transition-colors ${
                isComplete ? 'text-white/80' : 'text-white/40'
              }`}>
                <code>{fixedCode}</code>
              </pre>
            </motion.div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mt-6">
          {!isComplete ? (
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleRemediate}
              disabled={isRemediating}
              className="relative flex items-center gap-3 px-6 py-3 rounded-xl bg-gradient-to-r from-[#5c1a28] to-[#3d1018] text-white font-semibold disabled:opacity-50 transition-all overflow-hidden group"
            >
              <motion.div
                className="absolute inset-0 bg-white/20"
                initial={{ x: '-100%' }}
                whileHover={{ x: '100%' }}
                transition={{ duration: 0.5 }}
              />
              <Sparkles className="w-5 h-5 relative z-10" />
              <span className="relative z-10">
                {isRemediating ? 'AI is Fixing...' : 'Apply AI Remediation'}
              </span>
              <ArrowRight className="w-5 h-5 relative z-10 group-hover:translate-x-1 transition-transform" />
            </motion.button>
          ) : (
            <motion.button
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="flex items-center gap-3 px-6 py-3 rounded-xl bg-gradient-to-r from-emerald-600 to-emerald-700 text-white font-semibold transition-all"
            >
              <GitPullRequest className="w-5 h-5" />
              Create Secure PR
            </motion.button>
          )}
        </div>

        {/* Status Messages */}
        <AnimatePresence>
          {isRemediating && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="mt-4 text-center"
            >
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#5c1a28]/20 border border-[#5c1a28]/30">
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                >
                  <Shield className="w-4 h-4 text-[#8b3a4a]" />
                </motion.div>
                <span className="text-sm text-[#8b3a4a] font-medium">
                  Analyzing vulnerability patterns...
                </span>
              </div>
            </motion.div>
          )}
          {isComplete && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-4 text-center"
            >
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-emerald-500/10 border border-emerald-500/20">
                <Check className="w-4 h-4 text-emerald-400" />
                <span className="text-sm text-emerald-400 font-medium">
                  Vulnerability successfully remediated
                </span>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </GlassCard>
  )
}
