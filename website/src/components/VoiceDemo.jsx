import { motion } from 'framer-motion'

export default function VoiceDemo() {
  return (
    <section className="py-10 lg:py-14 bg-white border-y border-[#e8e8ed]">
      <div className="max-w-[1160px] mx-auto px-4 lg:px-6">
        <div className="grid lg:grid-cols-2 gap-8 items-center">
          <div className="rounded-[20px] bg-[#1d1d1f] p-5 lg:p-6 window-shadow overflow-hidden">
            <div className="flex items-center gap-2 text-white/60 text-[11px] font-mono tracking-[0.08em] uppercase">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" /> Live demo
            </div>
            <div className="mt-4 space-y-3 font-mono text-[13px]">
              <div className="flex items-center gap-3 text-white">
                <span className="w-7 h-7 rounded-full bg-white/10 grid place-items-center text-[10px]">\u25C9</span>
                <span>Hey Nova, open Brave and go to YouTube</span>
              </div>
              <div className="ml-10 rounded-lg bg-white/[0.06] border border-white/10 p-3">
                <div className="text-white/80">Opening Brave...</div>
                <div className="text-emerald-400 mt-1">\u2713 Brave is ready \u2014 navigating to YouTube</div>
              </div>
              <div className="ml-10 flex items-center gap-1 pt-1">
                {[10,18,14,24,16,12].map((h,i)=>(
                  <motion.span key={i} animate={{height:[h*0.6,h,h*0.6]}} transition={{duration:1, repeat:Infinity, delay:i*0.1}} className="w-[3px] rounded-full bg-emerald-400/70" style={{height:h}} />
                ))}
                <span className="ml-2 text-[10px] text-white/30">transcribing</span>
              </div>
            </div>
          </div>
          <div>
            <p className="text-[11px] font-semibold tracking-[0.16em] text-[#86868b] uppercase">Natural. Fast. Helpful.</p>
            <h3 className="mt-2 font-display text-[28px] lg:text-[34px] font-semibold tracking-[-0.03em] text-[#1d1d1f] leading-[1.05]">Just say it.</h3>
            <p className="mt-3 text-[14px] leading-relaxed text-[#6e6e73] max-w-[420px]">Talk to Nova like you would talk to a teammate. It understands what you mean and gets it done — no memorizing commands.</p>
            <div className="mt-5 flex flex-wrap gap-2">
              {["Open Notepad","Search YouTube","Scroll down","What\\u0027s on my screen?","Stop","Do that again"].map(c=>(
                <span key={c} className="px-3 py-1.5 rounded-full bg-[#f5f5f7] border border-[#e8e8ed] text-[11px] font-medium text-[#424245]">\u201C{c}\u201D</span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
