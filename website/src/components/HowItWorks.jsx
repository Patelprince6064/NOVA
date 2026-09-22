import { motion } from 'framer-motion'

const steps = [
  { n: '01', t: 'Say it', d: 'Say "Hey Nova" and speak naturally.' },
  { n: '02', t: 'Nova understands', d: 'Speech is converted into a command and interpreted intelligently.' },
  { n: '03', t: 'Nova acts', d: 'Nova safely performs the supported PC, browser, or visual action.' },
  { n: '04', t: 'Get it done', d: 'Nova confirms the result and stays ready for your next command.' },
]

export default function HowItWorks() {
  return (
    <section id="how-it-works" className="py-16 lg:py-24">
      <div className="max-w-[1200px] mx-auto px-6 lg:px-8">
        <h2 className="text-center font-display text-[32px] lg:text-[40px] font-semibold tracking-[-0.03em] text-white">How Nova works</h2>
        <div className="relative mt-10 lg:mt-14">
          <div className="hidden lg:block absolute top-[34px] left-[8%] right-[8%] h-[1px] bg-gradient-to-r from-transparent via-blue-500/30 to-transparent" />
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {steps.map((s,i)=>(
              <motion.div key={s.n} initial={{opacity:0,y:12}} whileInView={{opacity:1,y:0}} viewport={{once:true}} transition={{delay:i*0.08}} className="relative rounded-2xl bg-white/[0.03] border border-white/[0.06] p-6">
                <div className="w-8 h-8 rounded-full bg-white text-[#05070B] grid place-items-center text-[12px] font-bold">{s.n}</div>
                <h3 className="mt-4 text-[15px] font-semibold text-white">{s.t}</h3>
                <p className="mt-2 text-[13px] leading-relaxed text-white/45">{s.d}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
