import { motion } from 'framer-motion'

export default function Hero({ onDemo }) {
  return (
    <section id="home" className="relative min-h-[86vh] flex items-center v3-hero-grad overflow-hidden">
      <div className="max-w-[1160px] mx-auto px-4 lg:px-6 w-full py-12 lg:py-8">
        <div className="grid lg:grid-cols-[1.05fr_0.95fr] gap-8 lg:gap-6 items-center">
          {/* left text like infina */}
          <div className="pt-6 lg:pt-10">
            <motion.h1
              initial={{ opacity: 0, y: 18 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7 }}
              className="font-display font-semibold tracking-[-0.04em] leading-[0.9] text-[#1d1d1f]"
              style={{ fontSize: 'clamp(32px, 5vw, 52px)' }}
            >
              Talk to your PC
              <br />
              <span className="inline-flex items-baseline gap-2">
                <span className="text-[#1d1d1f]">hands-free</span>
                <span className="inline-flex items-center gap-1.5 text-[11px] font-sans font-medium tracking-[0.14em] uppercase text-[#6e6e73] ml-2 hidden sm:inline-flex">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" /> Nova
                </span>
              </span>
            </motion.h1>

            <motion.p
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.1 }}
              className="mt-5 max-w-[480px] text-[15px] lg:text-[16px] leading-[1.6] text-[#424245]"
            >
              Type, control, and automate Windows by voice. Works with Explorer, Office, Chrome, VS Code, or any app you use — no key to hold.
            </motion.p>

            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.18 }}
              className="mt-7 flex flex-wrap gap-3"
            >
              <a
                href={import.meta.env.VITE_DOWNLOAD_URL || '#download'}
                className="inline-flex items-center justify-center h-[42px] px-6 rounded-full bg-[#1d1d1f] text-white text-[14px] font-medium hover:bg-black hover:scale-[1.02] transition-all"
              >
                Try for free
              </a>
              <a
                href="#how-it-works"
                className="inline-flex items-center justify-center h-[42px] px-6 rounded-full bg-white border border-[#d2d2d7] text-[#1d1d1f] text-[14px] font-medium hover:bg-[#f5f5f7] transition-colors"
              >
                How it works
              </a>
            </motion.div>

            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.4 }}
              className="mt-4 text-[12px] text-[#86868b]"
            >
              Free to try \u00B7 2,000 words included \u00B7 No card required
            </motion.p>
          </div>

          {/* right - window mockup like infina narrator */}
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ duration: 0.9, delay: 0.2 }}
            className="relative lg:h-[520px] grid place-items-center py-6 lg:py-0"
          >
            {/* window shadow */}
            <div className="relative w-[320px] sm:w-[360px] lg:w-[380px] rounded-[18px] bg-white border border-[#e8e8ed] window-shadow overflow-hidden">
              {/* title bar */}
              <div className="h-9 flex items-center gap-1.5 px-4 border-b border-[#e8e8ed] bg-[#f5f5f7]/80">
                <span className="w-3 h-3 rounded-full bg-[#ff5f56] border border-black/10" />
                <span className="w-3 h-3 rounded-full bg-[#ffbd2e] border border-black/10" />
                <span className="w-3 h-3 rounded-full bg-[#27c93f] border border-black/10" />
                <span className="ml-3 text-[11px] font-medium text-[#6e6e73] tracking-wide">Nova \u2014 Voice Control</span>
              </div>
              {/* content - terminal like */}
              <div className="p-4 bg-white">
                <div className="rounded-xl bg-[#1d1d1f] text-white p-4 font-mono text-[12px] leading-relaxed">
                  <div className="flex items-center gap-2 text-white/60 text-[11px] mb-3">
                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" /> Listening \u2014 say \u201CHey Nova\u201D
                  </div>
                  <div className="space-y-2">
                    <div className="text-white/90">\u276F Hey Nova, open Brave.</div>
                    <div className="text-emerald-400">\u2713 Opening Brave...</div>
                    <div className="text-white/90">\u276F Search YouTube for Arijit Singh</div>
                    <div className="text-emerald-400">\u2713 Searching...</div>
                    <div className="flex items-center gap-1 pt-2">
                      {[8,16,12,22,14,10,18].map((h,i)=>(
                        <motion.span key={i} animate={{ height: [h*0.6, h, h*0.6] }} transition={{ duration: 1.1, repeat: Infinity, delay: i*0.1 }} className="w-[3px] rounded-full bg-emerald-400/80" style={{ height: h }} />
                      ))}
                      <span className="ml-2 text-[10px] text-white/40">voice waveform</span>
                    </div>
                  </div>
                </div>
                {/* app icons row */}
                <div className="mt-4 flex items-center gap-2 flex-wrap">
                  {["Brave","Chrome","VS Code","Explorer","YouTube"].map(a=>(
                    <span key={a} className="px-2.5 py-1 rounded-full bg-[#f5f5f7] border border-[#e8e8ed] text-[11px] font-medium text-[#424245]">{a}</span>
                  ))}
                </div>
                <div className="mt-3 flex items-center justify-between text-[11px]">
                  <span className="text-[#86868b]">Works in any Windows app</span>
                  <span className="text-emerald-600 font-medium">\u25CF Ready</span>
                </div>
              </div>
            </div>

            {/* floating Hey Nova badge like infina narrator */}
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.8 }}
              className="absolute -bottom-1 lg:bottom-6 left-1/2 -translate-x-1/2 flex items-center gap-2 px-3 py-1.5 rounded-full bg-white border border-[#e8e8ed] shadow-sm text-[11px] font-medium text-[#1d1d1f]"
            >
              <span className="w-2 h-2 rounded-full bg-[#1d1d1f] animate-pulse" /> Hey Nova \u2014 try \u201Copen Notepad\u201D
            </motion.div>
          </motion.div>
        </div>
      </div>
    </section>
  )
}
