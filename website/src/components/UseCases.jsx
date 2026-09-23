import { motion } from 'framer-motion'
import { AppWindow, Globe, Zap, Users } from 'lucide-react'

const cards = [
  { icon: AppWindow, title: 'Desktop', desc: 'Files, apps, typing, keys — all by voice.', accent: 'indigo' },
  { icon: Globe, title: 'Browser', desc: 'Search, YouTube, navigation — stays in your window.', accent: 'sky' },
  { icon: Zap, title: 'Flow', desc: 'Stay in zone. Reduce clicks and context switches.', accent: 'violet' },
  { icon: Users, title: 'Everyone', desc: 'Students, devs, creators — no learning curve.', accent: 'emerald' },
]

export default function UseCases() {
  return (
    <section id="use-cases" className="py-12 lg:py-20 bg-[#F8FAFC] border-y border-slate-200">
      <div className="max-w-[1160px] mx-auto px-4 lg:px-6">
        <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4">
          <h2 className="font-display text-[26px] lg:text-[32px] font-semibold tracking-[-0.03em] text-slate-900 leading-[1.05]">Built for real life,<br/><span className="text-slate-400">not just demos.</span></h2>
          <p className="max-w-[380px] text-[13px] leading-relaxed text-slate-500">From quick opens to short chains, Nova fits Windows routines.</p>
        </div>
        <div className="mt-8 grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {cards.map((c,i)=>(
            <motion.div key={c.title} initial={{opacity:0,y:12}} whileInView={{opacity:1,y:0}} viewport={{once:true}} transition={{delay:i*0.07}} className="rounded-[20px] bg-white border border-slate-200 p-5 hover:shadow-[0_8px_24px_rgba(15,23,42,0.06)] hover:-translate-y-[2px] transition-all">
              <div className="w-10 h-10 rounded-xl bg-slate-50 border border-slate-200 grid place-items-center text-slate-700"><c.icon size={16} /></div>
              <h3 className="mt-4 text-[14px] font-semibold text-slate-900">{c.title}</h3>
              <p className="mt-1 text-[12px] leading-relaxed text-slate-500">{c.desc}</p>
              <div className="mt-4 h-1 rounded-full bg-slate-100 overflow-hidden"><motion.div initial={{width:0}} whileInView={{width:"72%"}} viewport={{once:true}} transition={{delay:0.4+i*0.05, duration:0.8}} className="h-full bg-indigo-500 rounded-full" /></div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
