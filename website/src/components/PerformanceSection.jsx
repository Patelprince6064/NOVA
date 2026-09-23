import { motion } from 'framer-motion'

export default function PerformanceSection(){
  return (
    <section className="py-12 lg:py-16 bg-[#f5f5f7] border-y border-[#e8e8ed]">
      <div className="max-w-[1160px] mx-auto px-4 lg:px-6">
        <div className="grid lg:grid-cols-[1.1fr_0.9fr] gap-6 items-center rounded-[20px] bg-white border border-[#e8e8ed] p-6 lg:p-8 window-shadow">
          <div>
            <h2 className="font-display text-[26px] font-semibold tracking-[-0.03em] text-[#1d1d1f]">Fast by design.</h2>
            <div className="mt-4 flex items-baseline gap-3">
              <span className="text-[22px] font-semibold text-[#1d1d1f]">Milliseconds</span>
              <span className="text-[10px] tracking-[0.12em] text-[#86868b] uppercase">Local commands</span>
            </div>
            <p className="mt-2 text-[13px] leading-relaxed text-[#6e6e73] max-w-[460px]">Simple commands run locally in milliseconds. AI only when natural-language understanding is needed.</p>
            <div className="mt-4 flex gap-2">
              <span className="px-3 py-1 rounded-full bg-[#1d1d1f] text-white text-[11px] font-medium">No unnecessary AI calls</span>
              <span className="px-3 py-1 rounded-full bg-[#f5f5f7] border border-[#e8e8ed] text-[#424245] text-[11px]">Ready when you are</span>
            </div>
          </div>
          <motion.div initial={{opacity:0,y:10}} whileInView={{opacity:1,y:0}} viewport={{once:true}} className="rounded-2xl bg-[#f5f5f7] border border-[#e8e8ed] p-5">
            <div className="text-[10px] tracking-[0.12em] text-[#86868b] uppercase">Benchmark (local)</div>
            <div className="mt-3 grid grid-cols-3 gap-3 text-center">
              <div><div className="text-[18px] font-semibold text-[#1d1d1f]">~25ms</div><div className="text-[10px] text-[#86868b]">Router</div></div>
              <div><div className="text-[18px] font-semibold text-[#1d1d1f]">~45ms</div><div className="text-[10px] text-[#86868b]">Total</div></div>
              <div><div className="text-[18px] font-semibold text-[#1d1d1f]">~1s</div><div className="text-[10px] text-[#86868b]">Voice+STT</div></div>
            </div>
            <div className="mt-3 text-[10px] text-[#86868b]">LLM 1-3s when used. Local router excludes STT.</div>
          </motion.div>
        </div>
      </div>
    </section>
  )
}
