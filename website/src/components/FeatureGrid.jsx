import { motion } from 'framer-motion'
import { Mic, Monitor, Globe, Sparkles, ScanSearch, Lock } from 'lucide-react'

const features = [
  { icon: Mic, title: 'Voice Control', desc: 'Talk naturally.\nFast responses without\nkeyboard or mouse.' },
  { icon: Monitor, title: 'PC Automation', desc: 'Open apps, type, click,\nscroll, and control\nyour computer.' },
  { icon: Globe, title: 'Browser Control', desc: 'Search, navigate,\nand interact with\nsupported websites.' },
  { icon: Sparkles, title: 'AI-Powered', desc: 'Understand natural\nlanguage, context, and\nmulti-step requests.' },
  { icon: ScanSearch, title: 'Screen Understanding', desc: 'Nova can understand\nwhat\\u2019s visible on your\nscreen when needed.' },
  { icon: Lock, title: 'Private & Secure', desc: 'Designed with local-first\nbehavior and controlled\nactions.' },
]

export default function FeatureGrid() {
  return (
    <section id="features" className="relative py-20 lg:py-28 bg-gray-50/50">
      <div className="max-w-[1200px] mx-auto px-6 lg:px-8">
        <div className="text-center max-w-[640px] mx-auto mb-12">
          <p className="text-[11px] font-semibold tracking-[0.16em] text-gray-400 uppercase mb-4">More than a voice assistant</p>
          <h2 className="font-display text-[40px] lg:text-[48px] font-semibold tracking-[-0.03em] text-gray-900 leading-[1.05]">Powerful. Private.<br />Practical.</h2>
          <p className="mt-4 text-[15px] leading-relaxed text-gray-500">Nova helps you get things done without leaving your flow.</p>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 lg:gap-5">
          {features.map((f, i) => (
            <motion.div
              key={f.title}
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.06 }}
              className="group relative rounded-[20px] bg-white border border-gray-200 p-6 lg:p-7 hover:border-gray-300 hover:shadow-[0_4px_24px_rgba(0,0,0,0.06)] transition-all"
            >
              <div className="relative">
                <div className="w-9 h-9 rounded-xl bg-gray-900 grid place-items-center mb-4 text-white">
                  <f.icon size={16} />
                </div>
                <h3 className="text-[15px] font-semibold text-gray-900 mb-2">{f.title}</h3>
                <p className="text-[13px] leading-[1.6] text-gray-500 whitespace-pre-line">{f.desc}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
