import { motion } from 'framer-motion'

const chips = ["Open Notepad","Search YouTube","Scroll down","Explain what's on my screen","Stop","Do that again"]

export default function VoiceDemo() {
  return (
    <section className="py-10 lg:py-16">
      <div className="max-w-[1200px] mx-auto px-6 lg:px-8">
        <div className="grid lg:grid-cols-[1.1fr_0.9fr] gap-8 lg:gap-12 items-center rounded-[28px] bg-white/[0.02] border border-white/[0.06] p-6 lg:p-8 overflow-hidden">
          {/* left window */}
          <div className="relative rounded-[20px] bg-[#0B0D14] border border-white/[0.08] p-5 lg:p-6 overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-b from-blue-500/[0.04] to-transparent" />
            <div className="relative">
              <div className="flex items-center gap-3 text-white/80">
                <span className="w-8 h-8 rounded-full bg-white/10 grid place-items-center">🎙</span>
                <span className="text-[14px] font-medium">Hey Nova, open Brave.</span>
              </div>
              <div className="mt-4 flex items-center gap-1 text-white/30">
                <span className="w-1 h-1 rounded-full bg-white/40 animate-pulse" />
                <span className="w-1 h-1 rounded-full bg-white/40 animate-pulse [animation-delay:200ms]" />
                <span className="w-1 h-1 rounded-full bg-white/40 animate-pulse [animation-delay:400ms]" />
              </div>
              <div className="mt-6 rounded-xl bg-white/[0.04] border border-white/[0.06] p-4">
                <p className="text-[13px] text-white/60">Opening Brave...</p>
                <p className="mt-2 text-[13px] text-emerald-400">✓ Brave is ready.</p>
              </div>
              <div className="mt-6 flex items-center justify-center gap-1">
                {[6,14,10,20,12,8].map((h,i)=>(
                  <motion.span key={i} animate={{height:[h*0.6,h,h*0.6]}} transition={{duration:1.2, repeat:Infinity, delay:i*0.12}} className="w-[3px] rounded-full bg-blue-400/60" style={{height:h}} />
                ))}
              </div>
            </div>
          </div>

          {/* right */}
          <div>
            <p className="text-[11px] font-semibold tracking-[0.16em] text-white/40 uppercase">Natural. Fast. Helpful.</p>
            <h3 className="mt-3 font-display text-[34px] lg:text-[40px] font-semibold tracking-[-0.03em] text-white leading-[0.95]">Just say it.</h3>
            <p className="mt-4 text-[14px] leading-relaxed text-white/50 max-w-[420px]">Talk to Nova like you would talk to a teammate. It understands what you mean and gets it done.</p>
            <div className="mt-6 flex flex-wrap gap-2">
              {chips.map(c=>(
                <span key={c} className="px-3 py-1.5 rounded-full bg-white/[0.06] border border-white/[0.08] text-[12px] font-medium text-white/70 hover:bg-white/[0.08] hover:text-white transition-colors cursor-default">"{c}"</span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
