import { motion } from 'framer-motion'

export default function NovaOrb() {
  return (
    <div className="relative w-[320px] h-[320px] md:w-[440px] md:h-[440px] lg:w-[520px] lg:h-[520px] mx-auto">
      <div className="absolute inset-0 rounded-full bg-gradient-to-b from-gray-100 to-transparent blur-2xl" />
      <div className="absolute inset-[18%] rounded-full bg-blue-50/80 blur-3xl" />
      <motion.div
        animate={{ y: [0, -8, 0] }}
        transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut' }}
        className="absolute inset-0 grid place-items-center"
      >
        <div className="relative w-[68%] h-[68%] rounded-full">
          <div className="absolute inset-0 rounded-full p-[1px] bg-gradient-to-b from-gray-200 via-gray-100 to-white shadow-[0_8px_32px_rgba(0,0,0,0.06)]">
            <div className="w-full h-full rounded-full bg-white border border-gray-100" />
          </div>
          <div className="absolute inset-[8%] rounded-full border border-gray-100" />
          <div className="absolute inset-[14%] rounded-full border border-gray-100" />
          <motion.div
            animate={{ opacity: [0.3, 0.5, 0.3], scale: [1, 1.02, 1] }}
            transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
            className="absolute inset-0 rounded-full bg-gradient-to-b from-blue-50/60 to-transparent blur-xl"
          />
          <div className="absolute inset-0 grid place-items-center">
            <div className="flex items-center gap-[3px]">
              {[12, 24, 18, 32, 22, 28, 16].map((h, i) => (
                <motion.span
                  key={i}
                  animate={{ height: [h * 0.6, h, h * 0.7, h * 0.9, h * 0.6] }}
                  transition={{ duration: 1.8 + i * 0.15, repeat: Infinity, ease: 'easeInOut', delay: i * 0.1 }}
                  className="w-[3px] rounded-full bg-gradient-to-b from-gray-900 to-gray-600 shadow-sm"
                  style={{ height: h }}
                />
              ))}
            </div>
          </div>
          <div className="absolute top-[18%] left-[22%] w-[28%] h-[20%] rounded-full bg-gradient-to-br from-white to-transparent blur-xl opacity-60" />
        </div>
      </motion.div>
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6, duration: 0.8 }}
        className="absolute -bottom-2 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2"
      >
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white border border-gray-200 shadow-sm">
          <span className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)] animate-pulse" />
          <span className="text-[11px] font-medium tracking-[0.14em] text-gray-600 uppercase">Hey Nova</span>
        </div>
        <span className="text-[12px] text-gray-400">Ready when you are.</span>
      </motion.div>
      <motion.div
        animate={{ opacity: [0, 1, 0], y: [0, -20] }}
        transition={{ duration: 3, repeat: Infinity, delay: 0 }}
        className="absolute top-[12%] right-[18%] w-1 h-1 rounded-full bg-gray-300"
      />
      <motion.div
        animate={{ opacity: [0, 1, 0], y: [0, -16] }}
        transition={{ duration: 3.5, repeat: Infinity, delay: 1.2 }}
        className="absolute bottom-[20%] left-[14%] w-1 h-1 rounded-full bg-gray-300"
      />
    </div>
  )
}
