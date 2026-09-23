import { motion } from 'framer-motion'

const chips = ["Open Notepad","Search YouTube","Scroll down","Explain what\\u0027s on my screen","Stop","Do that again"]

export default function VoiceDemo() {
  return (
    <section className="py-10 lg:py-16 bg-white">
      <div className="max-w-[1200px] mx-auto px-6 lg:px-8">
        <div className="grid lg:grid-cols-[1.1fr_0.9fr] gap-8 lg:gap-12 items-center rounded-[28px] bg-gray-50 border border-gray-200 p-6 lg:p-8">
          <div className="relative rounded-[20px] bg-white border border-gray-200 p-5 lg:p-6 overflow-hidden shadow-sm">
            <div className="relative">
              <div className="flex items-center gap-3 text-gray-900">
                <span className="w-8 h-8 rounded-full bg-gray-900 grid place-items-center text-white text-[11px]">\u25C9</span>
                <span className="text-[14px] font-medium">Hey Nova, open Brave.</span>
              </div>
              <div className="mt-4 flex items-center gap-1 text-gray-300">
                <span className="w-1 h-1 rounded-full bg-gray-400 animate-pulse" />
                <span className="w-1 h-1 rounded-full bg-gray-400 animate-pulse [animation-delay:200ms]" />
                <span className="w-1 h-1 rounded-full bg-gray-400 animate-pulse [animation-delay:400ms]" />
              </div>
              <div className="mt-6 rounded-xl bg-gray-50 border border-gray-200 p-4">
                <p className="text-[13px] text-gray-600">Opening Brave...</p>
                <p className="mt-2 text-[13px] text-emerald-600">\u2713 Brave is ready.</p>
              </div>
              <div className="mt-6 flex items-center justify-center gap-1">
                {[6,14,10,20,12,8].map((h,i)=>(
                  <motion.span key={i} animate={{height:[h*0.6,h,h*0.6]}} transition={{duration:1.2, repeat:Infinity, delay:i*0.12}} className="w-[3px] rounded-full bg-gray-900/70" style={{height:h}} />
                ))}
              </div>
            </div>
          </div>
          <div>
            <p className="text-[11px] font-semibold tracking-[0.16em] text-gray-400 uppercase">Natural. Fast. Helpful.</p>
            <h3 className="mt-3 font-display text-[34px] lg:text-[40px] font-semibold tracking-[-0.03em] text-gray-900 leading-[0.95]">Just say it.</h3>
            <p className="mt-4 text-[14px] leading-relaxed text-gray-500 max-w-[420px]">Talk to Nova like you would talk to a teammate. It understands what you mean and gets it done.</p>
            <div className="mt-6 flex flex-wrap gap-2">
              {chips.map(c=>(
                <span key={c} className="px-3 py-1.5 rounded-full bg-white border border-gray-200 text-[12px] font-medium text-gray-600">"{c}"</span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
