'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Bot, X, Send, Sparkles, MessageSquare } from 'lucide-react'
import { cn } from '@/lib/utils'

const suggestedPrompts = [
  'Scan all repositories for vulnerabilities',
  'Show critical findings from last 24h',
  'Generate security report',
  'Explain the latest threat',
]

export function AICopilot() {
  const [isOpen, setIsOpen] = useState(false)
  const [message, setMessage] = useState('')
  const [messages, setMessages] = useState<Array<{ role: 'user' | 'assistant'; content: string }>>([
    {
      role: 'assistant',
      content: 'Welcome, Guardian. I am your AI Security Copilot. How may I assist you in protecting your repositories today?',
    },
  ])

  const handleSend = () => {
    if (!message.trim()) return
    
    setMessages((prev) => [...prev, { role: 'user', content: message }])
    setMessage('')
    
    // Simulate AI response
    setTimeout(() => {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Analyzing your request... I have identified 3 critical vulnerabilities in your codebase. Would you like me to initiate automated remediation?',
        },
      ])
    }, 1500)
  }

  return (
    <>
      {/* Floating Button */}
      <motion.button
        onClick={() => setIsOpen(true)}
        className={cn(
          'fixed bottom-6 right-6 z-50 p-4 rounded-2xl',
          'bg-gradient-to-br from-[#5c1a28] to-[#3d1018]',
          'border border-[#5c1a28]/60',
          'shadow-[0_0_40px_rgba(92,26,40,0.5)]',
          'transition-all duration-300',
          isOpen && 'scale-0 opacity-0'
        )}
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.95 }}
      >
        <Bot className="w-6 h-6 text-white" />
        <motion.div
          className="absolute inset-0 rounded-2xl bg-[#5c1a28]"
          animate={{ scale: [1, 1.2, 1], opacity: [0.5, 0, 0.5] }}
          transition={{ duration: 2, repeat: Infinity }}
        />
      </motion.button>

      {/* Chat Window */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 20 }}
            className="fixed bottom-6 right-6 z-50 w-[90vw] sm:w-[400px] max-h-[600px] rounded-2xl overflow-hidden"
          >
            {/* Glass background */}
            <div className="absolute inset-0 bg-[#0a0000]/90 backdrop-blur-xl" />
            <div className="absolute inset-0 border border-[#5c1a28]/40 rounded-2xl" />
            
            {/* Glow effect */}
            <div className="absolute inset-0 rounded-2xl shadow-[0_0_60px_rgba(92,26,40,0.4)]" />

            <div className="relative">
              {/* Header */}
              <div className="flex items-center justify-between p-4 border-b border-[#5c1a28]/30">
                <div className="flex items-center gap-3">
                  <div className="relative">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#5c1a28] to-[#3d1018] flex items-center justify-center">
                      <Bot className="w-5 h-5 text-white" />
                    </div>
                    <span className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-emerald-500 rounded-full border-2 border-[#0a0000]" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-white">Security Copilot</h3>
                    <p className="text-xs text-white/40">AI-powered assistant</p>
                  </div>
                </div>
                <motion.button
                  onClick={() => setIsOpen(false)}
                  whileHover={{ scale: 1.1 }}
                  whileTap={{ scale: 0.9 }}
                  className="p-2 rounded-lg hover:bg-white/10 transition-colors"
                >
                  <X className="w-5 h-5 text-white/60" />
                </motion.button>
              </div>

              {/* Messages */}
              <div className="h-[350px] overflow-y-auto p-4 space-y-4">
                {messages.map((msg, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={cn(
                      'flex gap-3',
                      msg.role === 'user' && 'flex-row-reverse'
                    )}
                  >
                    {msg.role === 'assistant' && (
                      <div className="w-8 h-8 rounded-lg bg-[#5c1a28]/30 flex items-center justify-center flex-shrink-0">
                        <Sparkles className="w-4 h-4 text-[#8b3a4a]" />
                      </div>
                    )}
                    <div
                      className={cn(
                        'max-w-[80%] p-3 rounded-xl text-sm',
                        msg.role === 'assistant'
                          ? 'bg-white/5 text-white/90 border border-white/10'
                          : 'bg-[#5c1a28]/30 text-white border border-[#5c1a28]/40'
                      )}
                    >
                      {msg.content}
                    </div>
                  </motion.div>
                ))}
              </div>

              {/* Suggested Prompts */}
              <div className="px-4 pb-2">
                <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-none">
                  {suggestedPrompts.map((prompt, i) => (
                    <motion.button
                      key={i}
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      onClick={() => setMessage(prompt)}
                      className="flex-shrink-0 px-3 py-1.5 rounded-full text-xs bg-white/5 border border-white/10 text-white/60 hover:text-white hover:border-[#5c1a28]/40 transition-all"
                    >
                      {prompt}
                    </motion.button>
                  ))}
                </div>
              </div>

              {/* Input */}
              <div className="p-4 border-t border-[#5c1a28]/30">
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                    placeholder="Ask your security copilot..."
                    className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-[#5c1a28]/60 transition-colors"
                  />
                  <motion.button
                    onClick={handleSend}
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    className="p-3 rounded-xl bg-gradient-to-br from-[#5c1a28] to-[#3d1018] text-white"
                  >
                    <Send className="w-5 h-5" />
                  </motion.button>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}
