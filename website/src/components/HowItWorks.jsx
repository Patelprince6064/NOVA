import { motion } from 'framer-motion'

const steps = [
  { n: '01', t: 'Wake', d: 'Say \u201CHey Nova\u201D \u2014 on-device Vosk listens only for that.', color: 'bg-indigo-600' },
  { n: '02', t: 'Speak', d: 'Faster-Whisper transcribes locally with silence stop.', color: 'bg-violet-600' },
  { n: '03', t: 'Act', d: 'Router or AI validates and runs allowlisted actions.', color: 'bg-sky-600' },
  { n: '04', t: 'Confirm', d: 'Nova speaks back and stays ready for follow-ups.', color: 'bg-emerald-600' },
]

export default function HowItWorks() {
  return (
    <section id="how-it-works" className="py-12 lg:py-20 bg-[#F8FAFC] border-y border-slate-200">
      <div className="max-w-[1160px] mx-auto px-4 lg:px-6">
        <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-6">
          <div>
            <p className="text-[11px] font-semibold tracking-[0.12em] text-indigo-600 uppercase">How it works</p>
            <h2 className="mt-2 font-display text-[26px] lg:text-[32px] font-semibold tracking-[-0.03em] text-slate-900">Say it. Done.</h2>
          </div>
          <p className="max-w-[420px] text-[13px] leading-relaxed text-slate-500">Four lightweight stages — no heavy background services, no cloud required for basics.</p>
        </div>

        <div className="relative mt-8">
          <div className="hidden lg:block absolute top-[32px] left-[8%] right-[8%] h-[2px] bg-gradient-to-r from-indigo-200 via-violet-200 to-sky-200 rounded-full" />
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {steps.map((s,i)=>(
              <motion.div key={s.n} initial={{opacity:0,y:12}} whileInView={{opacity:1,y:0}} viewport={{once:true}} transition={{delay:i*0.08}} className="relative rounded-2xl bg-white border border-slate-200 p-5 shadow-sm">
                <div className={"w-8 h-8 rounded-full " + s.color + " text-white grid place-items-center text-[11px] font-bold shadow-sm"}>{s.n}</div>
                <h3 className="mt-3 text-[14px] font-semibold text-slate-900">{s.t}</h3>
                <p className="mt-1 text-[12px] leading-relaxed text-slate-500">{s.d}</p>
                <div className="mt-3 flex items-center gap-1">
                  <span className="w-1 h-1 rounded-full bg-slate-300" /><span className="w-1 h-1 rounded-full bg-slate-300" /><span className="w-1 h-1 rounded-full bg-slate-300" />
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
