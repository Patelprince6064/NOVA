import { motion } from 'framer-motion'
import { Download, Play } from 'lucide-react'
import NovaOrb from './NovaOrb'

export default function Hero({ onDemo }) {
  return (
    <section id="home" className="relative overflow-hidden pt-[88px]">
      {/* background glows */}
      <div className="absolute inset-0 -z-10 bg-[#05070B]" />
      <div className="absolute -top-[200px] left-1/2 -translate-x-1/2 w-[1200px] h-[600px] bg-gradient-to-b from-blue-600/[0.08] via-blue-600/[0.03] to-transparent blur-3xl rounded-full" />
      <div className="absolute top-[280px] right-[10%] w-[500px] h-[500px] bg-blue-500/[0.04] blur-3xl rounded-full" />

      <div className="max-w-[1200px] mx-auto px-6 lg:px-8">
        <div className="grid lg:grid-cols-[1.05fr_1fr] gap-10 lg:gap-6 items-center py-10 lg:py-16">
          {/* left */}
          <div>
            <motion.p
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
              className="inline-flex items-center gap-2 text-[11px] font-semibold tracking-[0.16em] text-white/50 uppercase mb-6"
            >
              <span className="w-6 h-[1px] bg-white/20" />
              Your PC. Just a conversation away.
            </motion.p>

            <motion.h1
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.05 }}
              className="font-display font-semibold tracking-[-0.04em] leading-[0.9] text-white"
              style={{ fontSize: 'clamp(44px, 6vw, 72px)' }}
            >
              Meet Nova.<br />
              <span className="text-white/90">A smarter way</span><br />
              <span className="text-white/70">to use your computer.</span>
            </motion.h1>

            <motion.p
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.15 }}
              className="mt-6 max-w-[480px] text-[16px] lg:text-[18px] leading-[1.6] text-white/55"
            >
              Nova is a lightweight, hands-free Windows voice assistant that understands natural language
              and helps you control your PC, browser, and everyday apps.
            </motion.p>

            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.25 }}
              className="mt-8 flex flex-wrap gap-3"
            >
              <a
                href={import.meta.env.VITE_DOWNLOAD_URL || '#download'}
                className="inline-flex items-center gap-2 h-[46px] px-6 rounded-full bg-white text-[#05070B] font-medium text-[15px] hover:bg-white/90 hover:translate-y-[-1px] transition-all shadow-[0_8px_24px_rgba(255,255,255,0.12)]"
              >
                <Download size={16} />
                Download for Windows
              </a>
              <button
                onClick={onDemo}
                className="inline-flex items-center gap-2 h-[46px] px-6 rounded-full bg-white/[0.06] border border-white/10 text-white font-medium text-[15px] backdrop-blur hover:bg-white/[0.08] hover:border-white/15 transition-colors"
              >
                <span className="w-7 h-7 grid place-items-center rounded-full bg-white/10">
                  <Play size={12} className="ml-[1px] fill-white" />
                </span>
                Watch Demo
              </button>
            </motion.div>

            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.5 }}
              className="mt-5 text-[13px] text-white/30"
            >
              Free • Open source • Runs on your machine
            </motion.p>
          </div>

          {/* right orb */}
          <motion.div
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.9, delay: 0.2 }}
            className="relative lg:h-[560px] grid place-items-center"
          >
            <NovaOrb />
          </motion.div>
        </div>
      </div>
    </section>
  )
}
