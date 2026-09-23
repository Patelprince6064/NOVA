import { motion } from 'framer-motion'

export default function NovaOrb() {
  return (
    <div className="relative w-[280px] h-[280px] lg:w-[320px] lg:h-[320px] grid place-items-center">
      {/* pulse rings - Nova unique */}
      <motion.div animate={{ scale: [1, 1.12, 1], opacity: [0.15, 0.08, 0.15] }} transition={{ duration: 3, repeat: Infinity }} className="absolute inset-[12%] rounded-full border border-indigo-500/20 bg-indigo-500/5" />
      <motion.div animate={{ scale: [1, 1.08, 1], opacity: [0.2, 0.1, 0.2] }} transition={{ duration: 3, repeat: Infinity, delay: 0.5 }} className="absolute inset-[22%] rounded-full border border-violet-500/20 bg-violet-500/5" />

      {/* float */}
      <motion.div
        animate={{ y: [0, -6, 0] }}
        transition={{ duration: 5, repeat: Infinity, ease: 'easeInOut' }}
        className="relative w-[64%] h-[64%] rounded-full grid place-items-center"
      >
        {/* outer border */}
        <div className="absolute inset-0 rounded-full p-[1.5px] bg-gradient-to-b from-indigo-500/30 via-violet-500/20 to-transparent">
          <div className="w-full h-full rounded-full bg-white shadow-[0_8px_24px_rgba(79,70,229,0.12)] border border-indigo-100" />
        </div>

        {/* inner highlight */}
        <div className="absolute inset-[14%] rounded-full border border-indigo-100/80 bg-gradient-to-b from-white to-indigo-50/50" />

        {/* waveform center - Nova blue */}
        <div className="relative flex items-center gap-[3px]">
          {[14, 26, 18, 34, 20, 30, 16].map((h, i) => (
            <motion.span
              key={i}
              animate={{ height: [h * 0.55, h, h * 0.65, h * 0.9, h * 0.55] }}
              transition={{ duration: 1.6 + i * 0.12, repeat: Infinity, ease: 'easeInOut', delay: i * 0.08 }}
              className="w-[3px] rounded-full bg-gradient-to-b from-indigo-600 to-violet-600 shadow-[0_2px_8px_rgba(79,70,229,0.25)]"
              style={{ height: h }}
            />
          ))}
        </div>

        {/* mic icon overlay */}
        <div className="absolute -top-1 -right-1 w-7 h-7 rounded-full bg-indigo-600 border-2 border-white shadow-md grid place-items-center text-white">
          <span className="text-[11px]">\u25C9</span>
        </div>
      </motion.div>

      {/* label */}
      <motion.div
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6 }}
        className="absolute -bottom-1 left-1/2 -translate-x-1/2 flex flex-col items-center gap-1.5"
      >
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white border border-slate-200 shadow-sm">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-[11px] font-semibold tracking-[0.08em] text-slate-700">HEY NOVA</span>
          <span className="w-px h-3 bg-slate-200" />
          <span className="text-[11px] text-slate-500">Listening</span>
        </div>
      </motion.div>
    </div>
  )
}
