import { motion } from 'framer-motion'

const cmds = ["Open VS Code","Open YouTube","Search Python tutorials","Scroll down","Go back","Type hello world","What\\u2019s on my screen?","Stop","Try again","Open Brave","Open Notepad","Search lo-fi","Play first one","Go to Google","Refresh"]

export default function CommandShowcase(){
  return (
    <section id="commands" className="py-12 bg-white">
      <div className="max-w-[1160px] mx-auto px-4 lg:px-6 text-center">
        <p className="text-[11px] font-semibold tracking-[0.12em] text-indigo-600 uppercase">Commands</p>
        <h2 className="mt-2 font-display text-[26px] font-semibold tracking-[-0.03em] text-slate-900">Just talk to Nova.</h2>
        <p className="mt-2 text-[13px] text-slate-500">Natural phrasing, not memorized syntax.</p>
        <div className="mt-6 flex flex-wrap justify-center gap-2 max-w-[880px] mx-auto">
          {cmds.map((c,i)=>(
            <motion.span
              key={c+i}
              initial={{opacity:0, y:6}}
              whileInView={{opacity:1, y:0}}
              viewport={{once:true}}
              transition={{delay:(i%6)*0.04}}
              whileHover={{ y: -2, scale: 1.02 }}
              className="px-3.5 py-2 rounded-full bg-white border border-slate-200 text-[12px] font-medium text-slate-600 hover:border-indigo-200 hover:text-indigo-700 hover:shadow-sm transition-all cursor-default"
            >\u201C{c}\u201D</motion.span>
          ))}
        </div>
      </div>
    </section>
  )
}
