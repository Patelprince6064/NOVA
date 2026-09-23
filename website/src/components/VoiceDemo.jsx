import { motion } from 'framer-motion'
import { Mic, Volume2 } from 'lucide-react'

export default function VoiceDemo() {
  return (
    <section className="py-12 lg:py-16 bg-white">
      <div className="max-w-[1160px] mx-auto px-4 lg:px-6">
        <div className="grid lg:grid-cols-[1.05fr_0.95fr] gap-8 items-center">
          <div>
            <p className="inline-flex px-2 py-1 rounded-full bg-violet-50 border border-violet-200 text-[11px] font-semibold tracking-[0.08em] text-violet-700 uppercase">Live</p>
            <h3 className="mt-3 font-display text-[26px] lg:text-[32px] font-semibold tracking-[-0.03em] text-slate-900 leading-[1.05]">Talk like a teammate.</h3>
            <p className="mt-3 text-[14px] leading-relaxed text-slate-500 max-w-[440px]">No memorizing syntax. Nova understands intent and picks the right allowlisted tool.</p>
            <div className="mt-5 flex flex-wrap gap-2">
              {["Open Notepad","Search YouTube","Scroll down","What\\u2019s on my screen?","Stop"].map(c=>(
                <span key={c} className="px-3 py-1.5 rounded-full bg-white border border-slate-200 text-[12px] font-medium text-slate-600 hover:border-indigo-200 hover:text-indigo-700 transition-colors">\u201C{c}\u201D</span>
              ))}
            </div>
          </div>

          <div className="relative rounded-[20px] bg-slate-900 border border-slate-800 p-5 lg:p-6 overflow-hidden shadow-[0_16px_40px_rgba(15,23,42,0.18)]">
            <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/10 via-transparent to-violet-500/10" />
            <div className="relative">
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-2 text-[11px] font-medium tracking-wide text-white/60 uppercase"><span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" /> Nova listening</span>
                <span className="flex items-center gap-1 text-[11px] text-white/40"><Volume2 size={12} /> SAPI5</span>
              </div>
              <div className="mt-4 space-y-3">
                <div className="rounded-xl bg-white text-slate-900 px-4 py-3 text-[13px] font-medium shadow-sm">\u201CHey Nova, open Brave.\u201D</div>
                <div className="rounded-xl bg-indigo-600 text-white px-4 py-3 text-[13px] flex items-center gap-2"><Mic size={14} /> Opening Brave \u2014 <span className="text-white/70">listening for next</span></div>
              </div>
              <div className="mt-5 flex items-center gap-2">
                <div className="flex items-center gap-[3px] flex-1 p-3 rounded-full bg-white/5 border border-white/10">
                  {[8,16,12,24,14,18,10].map((h,i)=>(
                    <motion.span key={i} animate={{ height: [h*0.6, h, h*0.6] }} transition={{ duration: 0.9, repeat: Infinity, delay: i*0.08 }} className="w-[3px] rounded-full bg-indigo-400" style={{ height: h }} />
                  ))}
                  <span className="ml-2 text-[11px] text-white/50">waveform</span>
                </div>
                <span className="px-3 py-2 rounded-full bg-white text-slate-900 text-[12px] font-medium">Send</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
