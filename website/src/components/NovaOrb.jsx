import { motion } from 'framer-motion'

export default function NovaOrb() {
  return (
    <div className="relative w-[320px] h-[320px] md:w-[440px] md:h-[440px] lg:w-[520px] lg:h-[520px] mx-auto">
      {/* soft outer glow */}
      <div className="absolute inset-0 rounded-full bg-gradient-to-b from-blue-500/[0.08] to-transparent blur-2xl" />
      <div className="absolute inset-[18%] rounded-full bg-blue-500/[0.04] blur-3xl" />

      {/* floating container */}
      <motion.div
        animate={{ y: [0, -10, 0] }}
        transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut' }}
        className="absolute inset-0 grid place-items-center"
      >
        {/* outer ring */}
        <div className="relative w-[68%] h-[68%] rounded-full">
          {/* border gradient */}
          <div className="absolute inset-0 rounded-full p-[1px] bg-gradient-to-b from-white/30 via-blue-400/20 to-transparent">
            <div className="w-full h-full rounded-full bg-[#0A0E1A] border border-white/[0.04]" />
          </div>

          {/* inner glow ring */}
          <div className="absolute inset-[8%] rounded-full border border-blue-400/15" />
          <div className="absolute inset-[14%] rounded-full border border-white/[0.06]" />

          {/* breathing glow */}
          <motion.div
            animate={{ opacity: [0.4, 0.7, 0.4], scale: [1, 1.02, 1] }}
            transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
            className="absolute inset-0 rounded-full bg-gradient-to-b from-blue-500/10 to-transparent blur-xl"
          />

          {/* center waveform */}
          <div className="absolute inset-0 grid place-items-center">
            <div className="flex items-center gap-[3px]">
              {[12, 24, 18, 32, 22, 28, 16].map((h, i) => (
                <motion.span
                  key={i}
                  animate={{ height: [h * 0.6, h, h * 0.7, h * 0.9, h * 0.6] }}
                  transition={{ duration: 1.8 + i * 0.15, repeat: Infinity, ease: 'easeInOut', delay: i * 0.1 }}
                  className="w-[3px] rounded-full bg-gradient-to-b from-white to-blue-200 shadow-[0_0_8px_rgba(59,130,246,0.6)]"
                  style={{ height: h }}
                />
              ))}
            </div>
          </div>

          {/* subtle highlight */}
          <div className="absolute top-[18%] left-[22%] w-[28%] h-[20%] rounded-full bg-gradient-to-br from-white/12 to-transparent blur-xl" />
        </div>
      </motion.div>

      {/* hey nova label below orb */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6, duration: 0.8 }}
        className="absolute -bottom-2 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2"
      >
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/[0.04] border border-white/[0.06] backdrop-blur">
          <span className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)] animate-pulse" />
          <span className="text-[11px] font-medium tracking-[0.14em] text-white/70 uppercase">Hey Nova</span>
        </div>
        <span className="text-[12px] text-white/40">Ready when you are.</span>
      </motion.div>

      {/* particles */}
      <motion.div
        animate={{ opacity: [0, 1, 0], y: [0, -20] }}
        transition={{ duration: 3, repeat: Infinity, delay: 0 }}
        className="absolute top-[12%] right-[18%] w-1 h-1 rounded-full bg-blue-400/60 blur-[0.5px]"
      />
      <motion.div
        animate={{ opacity: [0, 1, 0], y: [0, -16] }}
        transition={{ duration: 3.5, repeat: Infinity, delay: 1.2 }}
        className="absolute bottom-[20%] left-[14%] w-1 h-1 rounded-full bg-white/40 blur-[0.5px]"
      />
    </div>
  )
}
