import { motion } from 'framer-motion'

export default function PerformanceSection(){
  return (
    <section className="py-12 lg:py-16">
      <div className="max-w-[1200px] mx-auto px-6 lg:px-8">
        <div className="grid lg:grid-cols-[1.1fr_0.9fr] gap-8 items-center rounded-[28px] bg-white/[0.02] border border-white/[0.06] p-6 lg:p-10 overflow-hidden relative">
          <div className="absolute inset-0 bg-gradient-to-r from-blue-600/[0.04] via-transparent to-transparent" />
          <div className="relative">
            <h2 className="font-display text-[34px] font-semibold tracking-[-0.03em] text-white">Fast by design.</h2>
            <div className="mt-6 space-y-3">
              <div className="flex items-baseline gap-3">
                <span className="text-[28px] font-semibold text-white tracking-[-0.02em]">Milliseconds</span>
                <span className="text-[12px] font-medium tracking-[0.12em] text-white/40 uppercase">Local commands</span>
              </div>
              <p className="text-[13px] leading-relaxed text-white/50 max-w-[460px]">Simple commands are handled locally whenever possible, while AI is used when natural-language understanding is actually needed.</p>
              <div className="flex flex-wrap gap-2 pt-2">
                <span className="px-3 py-1 rounded-full bg-white text-[#05070B] text-[12px] font-semibold">No unnecessary AI calls</span>
                <span className="px-3 py-1 rounded-full bg-white/[0.06] border border-white/10 text-white/70 text-[12px]">Ready when you are</span>
              </div>
            </div>
          </div>
          <motion.div initial={{opacity:0, y:10}} whileInView={{opacity:1,y:0}} viewport={{once:true}} className="relative rounded-2xl bg-[#0B0D14] border border-white/10 p-6">
            <div className="text-[11px] tracking-[0.12em] text-white/40 uppercase">Benchmark (local)</div>
            <div className="mt-3 grid grid-cols-3 gap-4 text-center">
              <div><div className="text-[22px] font-semibold text-white">~25ms</div><div className="text-[11px] text-white/40">Router</div></div>
              <div><div className="text-[22px] font-semibold text-white">~45ms</div><div className="text-[11px] text-white/40">Total</div></div>
              <div><div className="text-[22px] font-semibold text-white">~1s</div><div className="text-[11px] text-white/40">Voice + STT</div></div>
            </div>
            <div className="mt-4 text-[11px] text-white/30">Measured on local router; STT excluded. Real LLM 1–3s.</div>
          </motion.div>
        </div>
      </div>
    </section>
  )
}
