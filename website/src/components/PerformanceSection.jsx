import { motion } from 'framer-motion'

export default function PerformanceSection(){
  return (
    <section className="py-12 lg:py-16 bg-gray-50/50">
      <div className="max-w-[1200px] mx-auto px-6 lg:px-8">
        <div className="grid lg:grid-cols-[1.1fr_0.9fr] gap-8 items-center rounded-[28px] bg-white border border-gray-200 p-6 lg:p-10 overflow-hidden relative shadow-sm">
          <div className="relative">
            <h2 className="font-display text-[34px] font-semibold tracking-[-0.03em] text-gray-900">Fast by design.</h2>
            <div className="mt-6 space-y-3">
              <div className="flex items-baseline gap-3">
                <span className="text-[28px] font-semibold text-gray-900 tracking-[-0.02em]">Milliseconds</span>
                <span className="text-[12px] font-medium tracking-[0.12em] text-gray-400 uppercase">Local commands</span>
              </div>
              <p className="text-[13px] leading-relaxed text-gray-500 max-w-[460px]">Simple commands are handled locally whenever possible, while AI is used when natural-language understanding is actually needed.</p>
              <div className="flex flex-wrap gap-2 pt-2">
                <span className="px-3 py-1 rounded-full bg-gray-900 text-white text-[12px] font-semibold">No unnecessary AI calls</span>
                <span className="px-3 py-1 rounded-full bg-gray-100 border border-gray-200 text-gray-600 text-[12px]">Ready when you are</span>
              </div>
            </div>
          </div>
          <motion.div initial={{opacity:0, y:10}} whileInView={{opacity:1,y:0}} viewport={{once:true}} className="relative rounded-2xl bg-gray-50 border border-gray-200 p-6">
            <div className="text-[11px] tracking-[0.12em] text-gray-400 uppercase">Benchmark (local)</div>
            <div className="mt-3 grid grid-cols-3 gap-4 text-center">
              <div><div className="text-[22px] font-semibold text-gray-900">~25ms</div><div className="text-[11px] text-gray-400">Router</div></div>
              <div><div className="text-[22px] font-semibold text-gray-900">~45ms</div><div className="text-[11px] text-gray-400">Total</div></div>
              <div><div className="text-[22px] font-semibold text-gray-900">~1s</div><div className="text-[11px] text-gray-400">Voice + STT</div></div>
            </div>
            <div className="mt-4 text-[11px] text-gray-400">Measured on local router; STT excluded. Real LLM 1-3s.</div>
          </motion.div>
        </div>
      </div>
    </section>
  )
}
