import { motion } from 'framer-motion'

const steps = ["Hey Nova","Open Brave","Go to YouTube","Search Arijit Singh","Play the first result"]

export default function WorkflowDemo() {
  return (
    <section className="py-12 lg:py-16">
      <div className="max-w-[900px] mx-auto px-6 lg:px-8">
        <div className="text-center">
          <h2 className="font-display text-[32px] lg:text-[40px] font-semibold tracking-[-0.03em] text-white leading-[1.05]">From one command<br/>to getting it done.</h2>
        </div>
        <div className="mt-10 rounded-[24px] bg-white/[0.02] border border-white/[0.06] p-6 lg:p-8">
          <div className="flex flex-col items-center">
            {steps.map((s,i)=>(
              <div key={s} className="flex flex-col items-center w-full">
                <motion.div initial={{opacity:0, scale:0.95}} whileInView={{opacity:1, scale:1}} viewport={{once:true}} transition={{delay:i*0.15}} className={`w-full max-w-[420px] rounded-full border px-5 py-3 text-center text-[13px] font-medium ${i===0?'bg-white text-[#05070B] border-white':'bg-white/[0.06] border-white/[0.08] text-white/80'}`}>
                  {s}
                </motion.div>
                {i<steps.length-1 && <div className="w-[1px] h-6 bg-gradient-to-b from-blue-400/40 to-transparent my-1" />}
              </div>
            ))}
            <motion.div initial={{opacity:0}} whileInView={{opacity:1}} viewport={{once:true}} transition={{delay: steps.length*0.15 + 0.2}} className="mt-6 inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-[12px] font-medium text-emerald-400">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" /> Task completed
            </motion.div>
          </div>
          <p className="mt-6 text-center text-[12px] text-white/30">Short, useful workflows — not complex autonomy.</p>
        </div>
      </div>
    </section>
  )
}
