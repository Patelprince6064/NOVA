import { motion } from 'framer-motion'

export default function FeatureGrid() {
  return (
    <section className="py-16 lg:py-24 bg-[#f5f5f7] border-y border-[#e8e8ed]">
      <div className="max-w-[1160px] mx-auto px-4 lg:px-6">
        <div className="text-center max-w-[640px] mx-auto">
          <motion.h2 initial={{opacity:0,y:12}} whileInView={{opacity:1,y:0}} viewport={{once:true}} className="font-display text-[28px] lg:text-[38px] font-semibold tracking-[-0.03em] text-[#1d1d1f] leading-[1.1]">
            Typing. Push-to-talk. <span className="text-[#1d1d1f]">Hands-free.</span>
          </motion.h2>
          <motion.p initial={{opacity:0}} whileInView={{opacity:1}} viewport={{once:true}} transition={{delay:0.1}} className="mt-3 text-[14px] text-[#6e6e73]">
            Every other voice app stops at the second. Nova is the third.
          </motion.p>
        </div>

        <div className="mt-10 grid md:grid-cols-3 gap-4 lg:gap-5">
          {/* Typing - red ache */}
          <motion.div initial={{opacity:0,y:14}} whileInView={{opacity:1,y:0}} viewport={{once:true}} transition={{delay:0.05}} className="rounded-[20px] bg-white border border-[#e8e8ed] p-6 lg:p-6">
            <div className="w-full h-[160px] rounded-xl bg-[#f5f5f7] border border-[#e8e8ed] grid place-items-center overflow-hidden relative">
              {/* simple figure hunched */}
              <svg viewBox="0 0 200 120" className="w-[180px] h-[108px]">
                <rect x="20" y="85" width="60" height="4" rx="2" fill="#d2d2d7" />
                <rect x="30" y="55" width="40" height="30" rx="3" fill="#1d1d1f" />
                <rect x="110" y="50" width="70" height="42" rx="4" fill="white" stroke="#d2d2d7" />
                <rect x="115" y="58" width="60" height="26" rx="2" fill="#f5f5f7" />
                <circle cx="45" cy="35" r="12" fill="#d9a98c" />
                <path d="M 45 47 C 30 60, 30 85, 35 85" stroke="#1d1d1f" strokeWidth="3" fill="none" strokeLinecap="round" />
                <path d="M 48 55 C 55 65, 80 95, 95 88" stroke="#ff3b30" strokeWidth="2" fill="none" strokeLinecap="round" opacity="0.9" />
                <circle cx="95" cy="88" r="3" fill="#ff3b30" />
                <text x="100" y="18" fontSize="8" fill="#ff3b30" fontWeight="600">slow</text>
              </svg>
              <span className="absolute top-3 left-3 px-2 py-1 rounded-full bg-[#ff3b30]/10 text-[#ff3b30] text-[10px] font-semibold tracking-[0.08em] uppercase">Typing</span>
            </div>
            <h3 className="mt-4 text-[15px] font-semibold text-[#1d1d1f]">Hunched in, 45 wpm.</h3>
            <p className="mt-1.5 text-[13px] leading-[1.5] text-[#6e6e73]">Hands on keyboard, eyes on screen. Every prompt is manual.</p>
          </motion.div>

          {/* Push-to-talk - orange */}
          <motion.div initial={{opacity:0,y:14}} whileInView={{opacity:1,y:0}} viewport={{once:true}} transition={{delay:0.1}} className="rounded-[20px] bg-white border border-[#e8e8ed] p-6">
            <div className="w-full h-[160px] rounded-xl bg-[#f5f5f7] border border-[#e8e8ed] grid place-items-center overflow-hidden relative">
              <svg viewBox="0 0 200 120" className="w-[180px] h-[108px]">
                <rect x="20" y="85" width="60" height="4" rx="2" fill="#d2d2d7" />
                <rect x="30" y="55" width="40" height="30" rx="3" fill="#1d1d1f" />
                <rect x="110" y="50" width="70" height="42" rx="4" fill="white" stroke="#d2d2d7" />
                <rect x="135" y="72" width="18" height="10" rx="2" fill="#ff9500" stroke="#1d1d1f" strokeWidth="1.5" />
                <circle cx="45" cy="35" r="12" fill="#d9a98c" />
                <path d="M 45 47 C 35 58, 40 70, 60 78" stroke="#1d1d1f" strokeWidth="3" fill="none" strokeLinecap="round" />
                <circle cx="60" cy="78" r="3" fill="#ff9500" />
                <text x="100" y="18" fontSize="8" fill="#ff9500" fontWeight="600">hold key</text>
              </svg>
              <span className="absolute top-3 left-3 px-2 py-1 rounded-full bg-[#ff9500]/10 text-[#ff9500] text-[10px] font-semibold tracking-[0.08em] uppercase">Push-to-talk</span>
            </div>
            <h3 className="mt-4 text-[15px] font-semibold text-[#1d1d1f]">Every other app still starts with a key.</h3>
            <p className="mt-1.5 text-[13px] leading-[1.5] text-[#6e6e73]">Hold Option, speak, release. Hand still busy.</p>
          </motion.div>

          {/* Hands-free - only Nova - highlighted */}
          <motion.div initial={{opacity:0,y:14}} whileInView={{opacity:1,y:0}} viewport={{once:true}} transition={{delay:0.15}} className="rounded-[20px] bg-[#1d1d1f] border border-[#1d1d1f] p-6 text-white relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-b from-white/[0.06] to-transparent" />
            <div className="relative w-full h-[160px] rounded-xl bg-white/10 border border-white/10 grid place-items-center overflow-hidden">
              <svg viewBox="0 0 200 120" className="w-[180px] h-[108px]">
                <rect x="110" y="50" width="70" height="42" rx="4" fill="white" fillOpacity="0.95" />
                <rect x="115" y="58" width="60" height="26" rx="2" fill="#f5f5f7" />
                <g opacity="0.9">
                  <rect x="120" y="62" width="20" height="3" rx="1.5" fill="#1d1d1f" opacity="0.9" />
                  <rect x="120" y="68" width="35" height="3" rx="1.5" fill="#1d1d1f" opacity="0.6" />
                  <rect x="120" y="74" width="28" height="3" rx="1.5" fill="#1d1d1f" opacity="0.4" />
                </g>
                <circle cx="50" cy="40" r="12" fill="#d9a98c" />
                <path d="M 50 52 C 45 65, 55 75, 75 70" stroke="white" strokeWidth="3" fill="none" strokeLinecap="round" opacity="0.95" />
                <path d="M 75 70 C 85 68, 90 62, 95 55" stroke="white" strokeWidth="2.5" fill="none" strokeLinecap="round" opacity="0.7" />
                {/* sound bars */}
                <g fill="white">
                  <rect x="65" y="30" width="2" height="14" rx="1" opacity="0.95" />
                  <rect x="70" y="26" width="2" height="22" rx="1" opacity="0.85" />
                  <rect x="75" y="28" width="2" height="18" rx="1" opacity="0.75" />
                  <rect x="80" y="32" width="2" height="12" rx="1" opacity="0.6" />
                  <rect x="85" y="35" width="2" height="8" rx="1" opacity="0.4" />
                </g>
              </svg>
              <span className="absolute top-3 left-3 px-2 py-1 rounded-full bg-white text-[#1d1d1f] text-[10px] font-semibold tracking-[0.08em] uppercase">Hands-free \u00B7 only Nova</span>
            </div>
            <h3 className="relative mt-4 text-[15px] font-semibold text-white">No key, no click, nothing to touch.</h3>
            <p className="relative mt-1.5 text-[13px] leading-[1.5] text-white/60">Say \u201CHey Nova\u201D and speak. Typed, done.</p>
          </motion.div>
        </div>
      </div>
    </section>
  )
}
