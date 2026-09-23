import { motion } from 'framer-motion'
import { Mic, Monitor, Globe, Wand2, ScanEye, ShieldCheck } from 'lucide-react'

const features = [
  { icon: Mic, title: 'Voice First', desc: 'Natural language, not rigid commands. Say it how you think it.', color: 'indigo', grad: 'from-indigo-500 to-violet-500' },
  { icon: Monitor, title: 'PC Control', desc: 'Apps, files, typing, hotkeys — full desktop control by voice.', color: 'sky', grad: 'from-sky-500 to-cyan-500' },
  { icon: Globe, title: 'Browser Magic', desc: 'Open, search, navigate YouTube/Google — hands-free web.', color: 'emerald', grad: 'from-emerald-500 to-teal-500' },
  { icon: Wand2, title: 'Multi-step', desc: 'One sentence \u2192 many actions. Planner validates every step.', color: 'violet', grad: 'from-violet-500 to-fuchsia-500' },
  { icon: ScanEye, title: 'Sees Screen', desc: 'On-demand screenshot + vision finds what\u2019s on display.', color: 'amber', grad: 'from-amber-500 to-orange-500' },
  { icon: ShieldCheck, title: 'Private', desc: 'On-device wake + STT. No cloud unless you enable AI.', color: 'slate', grad: 'from-slate-700 to-slate-900' },
]

export default function FeatureGrid() {
  return (
    <section id="features" className="py-16 lg:py-24 bg-white">
      <div className="max-w-[1160px] mx-auto px-4 lg:px-6">
        <div className="max-w-[640px]">
          <p className="inline-flex px-2.5 py-1 rounded-full bg-indigo-50 border border-indigo-200 text-[11px] font-semibold tracking-[0.08em] text-indigo-700 uppercase">Features</p>
          <h2 className="mt-3 font-display text-[28px] lg:text-[36px] font-semibold tracking-[-0.03em] text-slate-900 leading-[1.1]">Everything you need.<br/><span className="text-slate-400">Nothing you don\u2019t.</span></h2>
          <p className="mt-3 text-[14px] leading-relaxed text-slate-500 max-w-[480px]">Nova is focused on real Windows tasks — fast, controlled, and transparent.</p>
        </div>

        <div className="mt-10 grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {features.map((f,i)=>(
            <motion.div key={f.title} initial={{opacity:0,y:12}} whileInView={{opacity:1,y:0}} viewport={{once:true}} transition={{delay:i*0.06}} className="group relative rounded-[20px] bg-white border border-slate-200 p-5 hover:border-slate-300 hover:shadow-[0_8px_24px_rgba(15,23,42,0.06)] hover:-translate-y-[2px] transition-all overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-br from-slate-50/0 via-transparent to-slate-50/0 group-hover:from-slate-50 transition-colors" />
              <div className="relative">
                <div className={"w-10 h-10 rounded-xl bg-gradient-to-br " + f.grad + " grid place-items-center text-white shadow-sm"}>
                  <f.icon size={18} />
                </div>
                {/* mini illustration area */}
                <div className="mt-4 h-[72px] rounded-xl bg-slate-50 border border-slate-200 grid place-items-center overflow-hidden relative">
                  <div className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-slate-300" />
                    <span className="w-16 h-1.5 rounded-full bg-slate-200" />
                    <span className="w-8 h-1.5 rounded-full bg-indigo-200" />
                  </div>
                  <div className="absolute bottom-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-indigo-200 to-transparent opacity-60" />
                </div>
                <h3 className="mt-4 text-[14px] font-semibold text-slate-900">{f.title}</h3>
                <p className="mt-1 text-[12px] leading-[1.6] text-slate-500">{f.desc}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
