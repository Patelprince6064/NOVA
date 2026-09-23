import { motion } from 'framer-motion'

export default function PerformanceSection(){
  return (
    <section className="py-12 lg:py-16 bg-[#F8FAFC] border-y border-slate-200">
      <div className="max-w-[1160px] mx-auto px-4 lg:px-6">
        <div className="grid lg:grid-cols-[1.1fr_0.9fr] gap-6 items-center">
          <div>
            <h2 className="font-display text-[24px] font-semibold tracking-[-0.03em] text-slate-900">Fast where it counts.</h2>
            <p className="mt-2 text-[13px] leading-relaxed text-slate-500 max-w-[460px]">Router handles common commands in milliseconds. Whisper + TTS are local. AI only when needed.</p>
            <div className="mt-4 flex gap-2">
              <span className="px-3 py-1 rounded-full bg-indigo-600 text-white text-[11px] font-medium">Local-first</span>
              <span className="px-3 py-1 rounded-full bg-white border border-slate-200 text-slate-600 text-[11px]">Reuse models</span>
            </div>
          </div>
          <motion.div initial={{opacity:0,y:10}} whileInView={{opacity:1,y:0}} viewport={{once:true}} className="rounded-2xl bg-white border border-slate-200 p-5 shadow-sm">
            <div className="text-[10px] tracking-[0.12em] text-slate-400 uppercase">Local benchmark</div>
            <div className="mt-3 grid grid-cols-3 gap-3 text-center">
              {["~25ms","~45ms","~0.9s"].map((v,i)=>(
                <div key={v} className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                  <div className="text-[16px] font-semibold text-slate-900">{v}</div>
                  <div className="text-[10px] text-slate-500">{["Router","Total","Voice" ][i]}</div>
                </div>
              ))}
            </div>
            <div className="mt-3 h-1.5 rounded-full bg-slate-100 overflow-hidden flex gap-1 p-1">
              <motion.div initial={{width:0}} whileInView={{width:"28%"}} transition={{duration:0.8}} className="h-full rounded-full bg-indigo-500" />
              <motion.div initial={{width:0}} whileInView={{width:"42%"}} transition={{duration:0.8, delay:0.15}} className="h-full rounded-full bg-violet-500" />
              <motion.div initial={{width:0}} whileInView={{width:"18%"}} transition={{duration:0.8, delay:0.3}} className="h-full rounded-full bg-slate-300" />
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  )
}
