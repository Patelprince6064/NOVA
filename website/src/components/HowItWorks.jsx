import { motion } from 'framer-motion'

const steps = [
  { n: '01', t: 'Say it', d: 'Say "Hey Nova" and speak naturally — no hotkey needed.', icon: '\u25CF' },
  { n: '02', t: 'Nova understands', d: 'On-device Whisper converts speech and routes to the right action.' },
  { n: '03', t: 'Nova acts', d: 'Opens apps, types, navigates browser, or checks your screen safely.' },
  { n: '04', t: 'Get it done', d: 'Nova confirms and stays ready for follow-ups without repeating wake word.' },
]

export default function HowItWorks() {
  return (
    <section id="how-it-works" className="py-16 lg:py-24 bg-white">
      <div className="max-w-[1160px] mx-auto px-4 lg:px-6">
        <div className="text-center max-w-[640px] mx-auto">
          <p className="text-[11px] font-semibold tracking-[0.16em] text-[#86868b] uppercase">How it works</p>
          <h2 className="mt-3 font-display text-[28px] lg:text-[36px] font-semibold tracking-[-0.03em] text-[#1d1d1f] leading-[1.1]">Open. Type. Send it.</h2>
          <p className="mt-3 text-[14px] text-[#6e6e73]">Three things you say, on repeat. That\u2019s the whole interface.</p>
          <p className="mt-2 text-[12px] text-[#86868b]">Prefer a key? Hold Left Option and it types what you say.</p>
        </div>

        <div className="relative mt-10">
          <div className="hidden lg:block absolute top-[34px] left-[10%] right-[10%] h-[1px] bg-[#e8e8ed]" />
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {steps.map((s,i)=>(
              <motion.div key={s.n} initial={{opacity:0,y:12}} whileInView={{opacity:1,y:0}} viewport={{once:true}} transition={{delay:i*0.07}} className="relative rounded-2xl bg-[#f5f5f7] border border-[#e8e8ed] p-6">
                <div className="w-8 h-8 rounded-full bg-[#1d1d1f] text-white grid place-items-center text-[11px] font-bold">{s.n}</div>
                <h3 className="mt-4 text-[14px] font-semibold text-[#1d1d1f]">{s.t}</h3>
                <p className="mt-2 text-[12px] leading-relaxed text-[#6e6e73]">{s.d}</p>
              </motion.div>
            ))}
          </div>
        </div>

        {/* app badge like infina */}
        <div className="mt-8 flex justify-center">
          <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#f5f5f7] border border-[#e8e8ed] text-[11px] font-medium text-[#424245]">
            <span className="w-1.5 h-1.5 rounded-full bg-[#1d1d1f]" /> Works with any Windows app
          </span>
        </div>
      </div>
    </section>
  )
}
