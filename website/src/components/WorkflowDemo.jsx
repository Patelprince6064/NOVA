import { motion } from 'framer-motion'

const steps = ["Hey Nova","Open Brave","Go to YouTube","Search Arijit Singh","Play the first result"]

export default function WorkflowDemo() {
  return (
    <section className="py-12 lg:py-16 bg-gray-50/50">
      <div className="max-w-[900px] mx-auto px-6 lg:px-8">
        <div className="text-center">
          <h2 className="font-display text-[32px] lg:text-[40px] font-semibold tracking-[-0.03em] text-gray-900 leading-[1.05]">From one command<br/>to getting it done.</h2>
        </div>
        <div className="mt-10 rounded-[24px] bg-white border border-gray-200 p-6 lg:p-8 shadow-sm">
          <div className="flex flex-col items-center">
            {steps.map((s,i)=>(
              <div key={s} className="flex flex-col items-center w-full">
                <motion.div initial={{opacity:0, scale:0.95}} whileInView={{opacity:1, scale:1}} viewport={{once:true}} transition={{delay:i*0.15}} className={`w-full max-w-[420px] rounded-full border px-5 py-3 text-center text-[13px] font-medium ${i===0?'bg-gray-900 text-white border-gray-900':'bg-gray-50 border-gray-200 text-gray-700'}`}>
                  {s}
                </motion.div>
                {i<steps.length-1 && <div className="w-[1px] h-6 bg-gray-200 my-1" />}
              </div>
            ))}
            <motion.div initial={{opacity:0}} whileInView={{opacity:1}} viewport={{once:true}} transition={{delay: steps.length*0.15 + 0.2}} className="mt-6 inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-50 border border-emerald-200 text-[12px] font-medium text-emerald-700">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" /> Task completed
            </motion.div>
          </div>
          <p className="mt-6 text-center text-[12px] text-gray-400">Short, useful workflows — not complex autonomy.</p>
        </div>
      </div>
    </section>
  )
}
