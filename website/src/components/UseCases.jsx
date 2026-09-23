import { motion } from 'framer-motion'
import { AppWindow, Globe, Zap, Users } from 'lucide-react'

const cards = [
  { icon: AppWindow, title: 'Apps & Files', desc: 'Open apps.\nType.\nNavigate.\nControl your desktop.' },
  { icon: Globe, title: 'Web & Research', desc: 'Open websites.\nSearch the web.\nNavigate browser pages.' },
  { icon: Zap, title: 'Productivity', desc: 'Stay focused.\nReduce repetitive actions.\nWork hands-free.' },
  { icon: Users, title: 'For Everyone', desc: 'Students.\nDevelopers.\nCreators.\nProfessionals.' },
]

export default function UseCases() {
  return (
    <section id="use-cases" className="py-12 lg:py-20 bg-white">
      <div className="max-w-[1200px] mx-auto px-6 lg:px-8">
        <div className="text-center max-w-[640px] mx-auto">
          <p className="text-[11px] font-semibold tracking-[0.16em] text-gray-400 uppercase">Built for real life</p>
          <h2 className="mt-3 font-display text-[34px] lg:text-[42px] font-semibold tracking-[-0.03em] text-gray-900 leading-[1.05]">Everything you need,<br/>in one assistant.</h2>
          <p className="mt-4 text-[14px] text-gray-500">From everyday tasks to short multi-step workflows, Nova fits naturally into your routine.</p>
        </div>
        <div className="mt-10 grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {cards.map((c,i)=>(
            <motion.div key={c.title} initial={{opacity:0,y:12}} whileInView={{opacity:1,y:0}} viewport={{once:true}} transition={{delay:i*0.07}} className="group relative rounded-[20px] bg-white border border-gray-200 p-6 hover:border-gray-300 hover:shadow-md transition-all">
              <div className="w-9 h-9 rounded-xl bg-gray-50 border border-gray-200 grid place-items-center text-gray-700"><c.icon size={16} /></div>
              <h3 className="mt-4 text-[15px] font-semibold text-gray-900">{c.title}</h3>
              <p className="mt-2 text-[13px] leading-relaxed text-gray-500 whitespace-pre-line">{c.desc}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
