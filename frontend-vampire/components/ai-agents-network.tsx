'use client'

import { useEffect, useState } from 'react'

import { motion } from 'framer-motion'

import {
  Brain,
  Shield,
  HeartPulse,
  Database,
  Zap,
} from 'lucide-react'

import { GlassCard } from './glass-card'

const baseAgents = [
  {
    id: 'Orchestrator Agent',
    icon: Brain,
    color: '#8b0000',
    position: { x: 50, y: 28 },
  },

  {
    id: 'Security Agent',
    icon: Shield,
    color: '#b91c1c',
    position: { x: 20, y: 62 },
  },

  {
    id: 'Repo Health Agent',
    icon: HeartPulse,
    color: '#7f1d1d',
    position: { x: 80, y: 62 },
  },

  {
    id: 'Memory Agent',
    icon: Database,
    color: '#5c1a28',
    position: { x: 50, y: 82 },
  },
]

const connections = [
  {
    from: 'Orchestrator Agent',
    to: 'Security Agent',
  },

  {
    from: 'Orchestrator Agent',
    to: 'Repo Health Agent',
  },

  {
    from: 'Orchestrator Agent',
    to: 'Memory Agent',
  },

  {
    from: 'Security Agent',
    to: 'Memory Agent',
  },

  {
    from: 'Repo Health Agent',
    to: 'Memory Agent',
  },
]

export function AIAgentsNetwork() {
  const [agentStatus, setAgentStatus] = useState<any>({})

  useEffect(() => {
    async function fetchStatus() {
      try {
        const response = await fetch(
          'http://127.0.0.1:8000/agent-status'
        )

        const data = await response.json()

        console.log('Agent Status:', data)

        setAgentStatus(data)
      } catch (error) {
        console.error(error)
      }
    }

    fetchStatus()

    const interval = setInterval(fetchStatus, 3000)

    return () => clearInterval(interval)
  }, [])

  return (
    <GlassCard delay={0.3}>
      <div className="p-6 lg:p-8">
        {/* HEADER */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-2xl font-bold text-white flex items-center gap-3">
              <Zap className="w-6 h-6 text-[#8b0000]" />

              Autonomous AI Agents
            </h2>

            <p className="text-white/40 text-sm mt-1">
              Real-time orchestration network
            </p>
          </div>

          <div className="flex items-center gap-2">
            <motion.div
              animate={{
                opacity: [1, 0.3, 1],
              }}
              transition={{
                duration: 1,
                repeat: Infinity,
              }}
              className="w-2 h-2 rounded-full bg-red-500"
            />

            <span className="text-xs text-red-400 font-mono">
              LIVE AI NETWORK
            </span>
          </div>
        </div>

        {/* NETWORK */}
        <div className="relative h-[420px] overflow-hidden rounded-3xl border border-white/10 bg-black/30 backdrop-blur-xl">
          {/* GRID */}
          <div className="absolute inset-0 opacity-10">
            <div
              className="w-full h-full"
              style={{
                backgroundImage:
                  'linear-gradient(rgba(255,255,255,0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.08) 1px, transparent 1px)',
                backgroundSize: '40px 40px',
              }}
            />
          </div>

          {/* SVG CONNECTIONS */}
          <svg
            className="absolute inset-0 w-full h-full"
            style={{
              overflow: 'visible',
            }}
          >
            <defs>
              <linearGradient
                id="bloodLine"
                x1="0%"
                y1="0%"
                x2="100%"
                y2="0%"
              >
                <stop
                  offset="0%"
                  stopColor="#8b0000"
                  stopOpacity="0.1"
                />

                <stop
                  offset="50%"
                  stopColor="#ff003c"
                  stopOpacity="1"
                />

                <stop
                  offset="100%"
                  stopColor="#8b0000"
                  stopOpacity="0.1"
                />
              </linearGradient>

              <filter id="glow">
                <feGaussianBlur
                  stdDeviation="4"
                  result="coloredBlur"
                />

                <feMerge>
                  <feMergeNode in="coloredBlur" />

                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>

            {connections.map((conn, i) => {
              const fromAgent = baseAgents.find(
                (a) => a.id === conn.from
              )

              const toAgent = baseAgents.find(
                (a) => a.id === conn.to
              )

              if (!fromAgent || !toAgent) return null

              return (
                <motion.line
                  key={i}
                  x1={`${fromAgent.position.x}%`}
                  y1={`${fromAgent.position.y}%`}
                  x2={`${toAgent.position.x}%`}
                  y2={`${toAgent.position.y}%`}
                  stroke="url(#bloodLine)"
                  strokeWidth="2"
                  filter="url(#glow)"
                  initial={{
                    pathLength: 0,
                    opacity: 0,
                  }}
                  animate={{
                    pathLength: 1,
                    opacity: 1,
                  }}
                  transition={{
                    duration: 1.2,
                    delay: i * 0.2,
                  }}
                />
              )
            })}

            {/* FLOW PARTICLES */}
            {connections.map((conn, i) => {
              const fromAgent = baseAgents.find(
                (a) => a.id === conn.from
              )

              const toAgent = baseAgents.find(
                (a) => a.id === conn.to
              )

              if (!fromAgent || !toAgent) return null

              return (
                <motion.circle
                  key={`particle-${i}`}
                  r="4"
                  fill="#ff003c"
                  filter="url(#glow)"
                  initial={{
                    cx: `${fromAgent.position.x}%`,
                    cy: `${fromAgent.position.y}%`,
                  }}
                  animate={{
                    cx: [
                      `${fromAgent.position.x}%`,
                      `${toAgent.position.x}%`,
                    ],

                    cy: [
                      `${fromAgent.position.y}%`,
                      `${toAgent.position.y}%`,
                    ],
                  }}
                  transition={{
                    duration: 2,
                    delay: i * 0.3,
                    repeat: Infinity,
                    ease: 'linear',
                  }}
                />
              )
            })}
          </svg>

          {/* AGENT NODES */}
          {baseAgents.map((agent, i) => {
            const status =
              agentStatus[agent.id] || 'IDLE'

            const isActive =
              status === 'ACTIVE' ||
              status === 'SCANNING'

            return (
              <motion.div
                key={agent.id}
                className="absolute -translate-x-1/2 -translate-y-1/2"
                style={{
                  left: `${agent.position.x}%`,
                  top: `${agent.position.y}%`,
                }}
                initial={{
                  opacity: 0,
                  scale: 0,
                }}
                animate={{
                  opacity: 1,
                  scale: 1,
                }}
                transition={{
                  delay: 0.4 + i * 0.1,
                  type: 'spring',
                }}
              >
                {/* OUTER RINGS */}
                <motion.div
                  animate={{
                    rotate: 360,
                  }}
                  transition={{
                    duration: 25,
                    repeat: Infinity,
                    ease: 'linear',
                  }}
                  className="absolute inset-0 w-28 h-28 -m-6 rounded-full border border-white/10"
                />

                <motion.div
                  animate={{
                    rotate: -360,
                  }}
                  transition={{
                    duration: 15,
                    repeat: Infinity,
                    ease: 'linear',
                  }}
                  className="absolute inset-0 w-24 h-24 -m-4 rounded-full border border-red-500/20"
                />

                {/* PULSE */}
                <motion.div
                  animate={{
                    scale: [1, 1.6, 1],
                    opacity: [0.4, 0, 0.4],
                  }}
                  transition={{
                    duration: 2,
                    repeat: Infinity,
                  }}
                  className="absolute inset-0 w-20 h-20 rounded-full"
                  style={{
                    background: agent.color,
                  }}
                />

                {/* MAIN NODE */}
                <motion.div
                  whileHover={{
                    scale: 1.08,
                  }}
                  className="relative w-20 h-20 rounded-full border border-white/20 bg-gradient-to-br from-[#1a0005] to-black flex items-center justify-center backdrop-blur-xl cursor-pointer"
                  style={{
                    boxShadow: `0 0 40px ${agent.color}70`,
                  }}
                >
                  <agent.icon className="w-8 h-8 text-white" />

                  {/* STATUS */}
                  <span
                    className={`absolute -top-1 -right-1 w-4 h-4 rounded-full border-2 border-black ${
                      isActive
                        ? 'bg-green-500'
                        : 'bg-gray-500'
                    } animate-pulse`}
                  />
                </motion.div>

                {/* LABEL */}
                <div className="absolute top-full mt-4 left-1/2 -translate-x-1/2 text-center whitespace-nowrap">
                  <p className="text-sm font-semibold text-white">
                    {agent.id}
                  </p>

                  <p
                    className={`text-xs font-mono ${
                      isActive
                        ? 'text-green-400'
                        : 'text-gray-400'
                    }`}
                  >
                    {status}
                  </p>
                </div>
              </motion.div>
            )
          })}

          {/* CORE */}
          <motion.div
            animate={{
              scale: [1, 1.2, 1],
              opacity: [0.3, 0.7, 0.3],
            }}
            transition={{
              duration: 3,
              repeat: Infinity,
            }}
            className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2"
          >
            <div className="w-24 h-24 rounded-full bg-red-900/20 blur-3xl" />
          </motion.div>
        </div>
      </div>
    </GlassCard>
  )
}