import { motion } from 'framer-motion'
import { ArrowDown, Check } from 'lucide-react'

const steps = ["Hey Nova", "Open Brave", "Go to YouTube", "Search lo-fi beats", "Play first result"]

export default function WorkflowDemo() {
  return (
    <section className="py-12 lg:py-16 bg-white">
      <div className="max-w-[860px] mx-auto px-4 lg:px-6">
        <div className="text-center max-w-[560px] mx-auto">
          <p className="text-[11px] font-semibold tracking-[0.12em] text-indigo-600 uppercase">Workflow</p>
          <h2 className="mt-2 font-display text-[26px] lg:text-[32px] font-semibold tracking-[-0.03em] text-slate-900 leading-[1.1]">One sentence,<br/>five actions.</h2>
          <p className="mt-3 text-[13px] text-slate-500">Short useful chains — not complex autonomy. Planner caps at 8 steps.</p>
        </div>

        <div className="mt-8 rounded-[20px] bg-[#F8FAFC] border border-slate-200 p-6 lg:p-8">
          <div className="flex flex-col items-center">
            {steps.map((s,i)=>(
              <div key={s} className="flex flex-col items-center w-full">
                <motion.div initial={{opacity:0, scale:0.96}} whileInView={{opacity:1, scale:1}} viewport={{once:true}} transition={{delay:i*0.12}} className={"w-full max-w-[460px] rounded-full px-5 py-3 text-center text-[13px] font-medium border shadow-sm " + (i===0 ? "bg-slate-900 text-white border-slate-900" : i===steps.length-1 ? "bg-emerald-600 text-white border-emerald-600" : "bg-white border-slate-200 text-slate-700")}>
                  {s}
                </motion.div>
                {i<steps.length-1 && <div className="my-1.5 w-8 h-8 rounded-full bg-white border border-slate-200 grid place-items-center shadow-sm"><ArrowDown size={12} className="text-slate-400" /></div>}
              </div>
            ))}
            <motion.div initial={{opacity:0}} whileInView={{opacity:1}} viewport={{once:true}} transition={{delay: steps.length*0.12}} className="mt-5 inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-50 border border-emerald-200 text-[12px] font-medium text-emerald-700">
              <Check size={12} /> Completed in ~4s
            </motion.div>
          </div>
        </div>
      </div>
    </section>
  )
}
