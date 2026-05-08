'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Shield, 
  Search, 
  Bell, 
  Bot, 
  LayoutDashboard, 
  GitPullRequest, 
  AlertTriangle, 
  Users, 
  FileBarChart,
  Menu,
  X
} from 'lucide-react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'

const navItems = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'PR Feed', href: '/pr-feed', icon: GitPullRequest },
  { name: 'Findings', href: '/findings', icon: AlertTriangle },
  { name: 'Developers', href: '/developers', icon: Users },
  { name: 'Reports', href: '/reports', icon: FileBarChart },
]

export function Navbar() {
  const pathname = usePathname()
  const [searchFocused, setSearchFocused] = useState(false)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  return (
    <motion.nav
      initial={{ y: -100, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.6, ease: 'easeOut' }}
      className="fixed top-0 left-0 right-0 z-50"
    >
      {/* Navbar Background */}
      <div className="absolute inset-0 bg-[#050505]/80 backdrop-blur-xl border-b border-[#5c1a28]/30" />
      
      <div className="relative max-w-[1800px] mx-auto px-4 lg:px-8">
        <div className="flex items-center justify-between h-16 lg:h-20">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-3 group">
            <motion.div
              className="relative"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <div className="absolute inset-0 bg-[#5c1a28] blur-xl opacity-50 group-hover:opacity-80 transition-opacity" />
              <div className="relative w-10 h-10 lg:w-12 lg:h-12 rounded-xl bg-gradient-to-br from-[#5c1a28] to-[#3d1018] flex items-center justify-center border border-[#5c1a28]/50">
                <Shield className="w-5 h-5 lg:w-6 lg:h-6 text-white" />
              </div>
            </motion.div>
            <div className="hidden sm:block">
              <h1 className="text-lg lg:text-xl font-bold text-white tracking-tight">
                Repo<span className="text-[#8b3a4a] text-glow">Guardian</span>
              </h1>
              <p className="text-[10px] lg:text-xs text-white/50 font-mono tracking-widest">
                AI SECURITY
              </p>
            </div>
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden lg:flex items-center gap-1">
            {navItems.map((item) => {
              const isActive = pathname === item.href
              return (
                <Link key={item.name} href={item.href}>
                  <motion.div
                    className={cn(
                      'relative px-4 py-2 rounded-lg flex items-center gap-2 transition-all duration-300',
                      isActive 
                        ? 'text-white' 
                        : 'text-white/60 hover:text-white'
                    )}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                  >
                    {isActive && (
                      <motion.div
                        layoutId="navIndicator"
                        className="absolute inset-0 bg-[#5c1a28]/30 border border-[#5c1a28]/40 rounded-lg"
                        transition={{ type: 'spring', bounce: 0.2, duration: 0.6 }}
                      />
                    )}
                    <item.icon className={cn(
                      'w-4 h-4 relative z-10 transition-colors',
                      isActive && 'text-[#8b3a4a]'
                    )} />
                    <span className="relative z-10 text-sm font-medium">{item.name}</span>
                  </motion.div>
                </Link>
              )
            })}
          </div>

          {/* Right Section */}
          <div className="flex items-center gap-2 lg:gap-4">
            {/* Search Bar */}
            <motion.div
              className={cn(
                'hidden md:flex items-center gap-2 px-3 lg:px-4 py-2 rounded-xl transition-all duration-300',
                'bg-[#2d0a12]/50 border',
                searchFocused 
                  ? 'border-[#5c1a28]/60 shadow-[0_0_20px_rgba(92,26,40,0.3)]' 
                  : 'border-white/10'
              )}
              animate={{ width: searchFocused ? 280 : 200 }}
            >
              <Search className="w-4 h-4 text-white/50" />
              <input
                type="text"
                placeholder="Search threats..."
                className="bg-transparent border-none outline-none text-sm text-white placeholder:text-white/30 w-full"
                onFocus={() => setSearchFocused(true)}
                onBlur={() => setSearchFocused(false)}
              />
              <kbd className="hidden lg:inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-mono text-white/30 bg-white/5 rounded border border-white/10">
                ⌘K
              </kbd>
            </motion.div>

            {/* Notifications */}
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="relative p-2 lg:p-2.5 rounded-xl bg-[#2d0a12]/50 border border-white/10 hover:border-[#5c1a28]/40 transition-all"
            >
              <Bell className="w-4 h-4 lg:w-5 lg:h-5 text-white/70" />
              <span className="absolute top-1 right-1 w-2 h-2 bg-[#5c1a28] rounded-full animate-pulse" />
            </motion.button>

            {/* AI Assistant */}
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="relative p-2 lg:p-2.5 rounded-xl bg-gradient-to-br from-[#5c1a28]/30 to-[#3d1018]/30 border border-[#5c1a28]/40 hover:border-[#5c1a28]/60 transition-all group"
            >
              <Bot className="w-4 h-4 lg:w-5 lg:h-5 text-[#8b3a4a] group-hover:text-white transition-colors" />
              <div className="absolute inset-0 bg-[#5c1a28]/30 rounded-xl blur-xl opacity-0 group-hover:opacity-100 transition-opacity" />
            </motion.button>

            {/* Mobile Menu Button */}
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="lg:hidden p-2 rounded-xl bg-[#2d0a12]/50 border border-white/10"
            >
              {mobileMenuOpen ? (
                <X className="w-5 h-5 text-white" />
              ) : (
                <Menu className="w-5 h-5 text-white" />
              )}
            </motion.button>
          </div>
        </div>
      </div>

      {/* Mobile Menu */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="lg:hidden border-t border-[#5c1a28]/30 bg-[#050505]/95 backdrop-blur-xl"
          >
            <div className="px-4 py-4 space-y-2">
              {navItems.map((item) => {
                const isActive = pathname === item.href
                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    onClick={() => setMobileMenuOpen(false)}
                  >
                    <motion.div
                      className={cn(
                        'flex items-center gap-3 px-4 py-3 rounded-xl transition-all',
                        isActive
                          ? 'bg-[#5c1a28]/30 border border-[#5c1a28]/40 text-white'
                          : 'text-white/60 hover:bg-white/5'
                      )}
                      whileTap={{ scale: 0.98 }}
                    >
                      <item.icon className={cn('w-5 h-5', isActive && 'text-[#8b3a4a]')} />
                      <span className="font-medium">{item.name}</span>
                    </motion.div>
                  </Link>
                )
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.nav>
  )
}
