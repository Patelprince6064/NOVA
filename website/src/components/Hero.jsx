import { motion } from 'framer-motion'
import { Sparkles, Mic, ArrowRight, Play } from 'lucide-react'
import NovaOrb from './NovaOrb'

export default function Hero({ onDemo }) {
  return (
    <section id="home" className="relative overflow-hidden pt-[72px]">
      {/* custom mesh bg */}
      <div className="absolute inset-0 -z-10 bg-[#FCFCF9]" />
      <div className="absolute -top-[120px] left-1/2 -translate-x-1/2 w-[1000px] h-[520px] bg-gradient-to-b from-indigo-500/[0.07] via-violet-500/[0.03] to-transparent blur-3xl rounded-full" />
      <div className="absolute top-[40%] right-[8%] w-[400px] h-[400px] bg-sky-500/[0.04] blur-3xl rounded-full" />

      <div className="max-w-[1160px] mx-auto px-4 lg:px-6">
        {/* centered hero like Linear/Infina but Nova own */}
        <div className="text-center pt-10 lg:pt-16 pb-8">
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white border border-slate-200 shadow-sm text-[12px] font-medium text-slate-600"
          >
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <Sparkles size={12} className="text-indigo-500" />
            Nova for Windows \u00B7 Free & Open Source
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.06 }}
            className="mt-6 font-display font-semibold tracking-[-0.04em] leading-[0.9] text-slate-900"
            style={{ fontSize: 'clamp(36px, 6vw, 64px)' }}
          >
            Your PC,
            <br />
            <span className="bg-gradient-to-r from-indigo-600 via-violet-600 to-indigo-600 bg-clip-text text-transparent">on voice.</span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.12 }}
            className="mt-5 max-w-[560px] mx-auto text-[16px] lg:text-[18px] leading-[1.6] text-slate-500"
          >
            Lightweight hands-free assistant that understands natural language and controls your PC, browser, and apps — no keyboard needed.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.18 }}
            className="mt-7 flex flex-wrap justify-center gap-3"
          >
            <a
              href={import.meta.env.VITE_DOWNLOAD_URL || '#download'}
              className="inline-flex items-center gap-2 h-[44px] px-6 rounded-full bg-indigo-600 text-white font-medium text-[14px] hover:bg-indigo-700 hover:shadow-[0_8px_20px_rgba(79,70,229,0.25)] hover:-translate-y-[1px] transition-all"
            >
              <Mic size={16} /> Download for Windows <ArrowRight size={14} />
            </a>
            <button
              onClick={onDemo}
              className="inline-flex items-center gap-2 h-[44px] px-6 rounded-full bg-white border border-slate-200 text-slate-700 font-medium text-[14px] hover:bg-slate-50 hover:border-slate-300 transition-colors shadow-sm"
            >
              <span className="w-7 h-7 rounded-full bg-slate-900 grid place-items-center"><Play size={11} className="ml-[1px] fill-white text-white" /></span>
              Watch 30s demo
            </button>
          </motion.div>

          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4 }}
            className="mt-4 text-[12px] text-slate-400"
          >
            Windows 10/11 \u00B7 Python 3.11+ \u00B7 Mic + speakers \u00B7 No account required
          </motion.p>
        </div>

        {/* custom window mockup - Nova unique bento */}
        <motion.div
          initial={{ opacity: 0, y: 20, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.9, delay: 0.25 }}
          className="relative max-w-[920px] mx-auto"
        >
          {/* floating chips around window */}
          <div className="hidden lg:block absolute -left-6 top-[18%] z-10">
            <motion.div animate={{ y: [0, -4, 0] }} transition={{ duration: 5, repeat: Infinity }} className="px-3 py-2 rounded-full bg-white border border-slate-200 shadow-[0_4px_16px_rgba(15,23,42,0.08)] text-[12px] font-medium text-slate-700">
              \u201COpen Brave\u201D
            </motion.div>
          </div>
          <div className="hidden lg:block absolute -right-4 top-[12%] z-10">
            <motion.div animate={{ y: [0, -5, 0] }} transition={{ duration: 6, repeat: Infinity, delay: 0.5 }} className="px-3 py-2 rounded-full bg-indigo-600 text-white shadow-[0_8px_20px_rgba(79,70,229,0.25)] text-[12px] font-medium">
              \u2713 Done
            </motion.div>
          </div>
          <div className="hidden lg:block absolute -left-2 bottom-[22%] z-10">
            <motion.div animate={{ y: [0, -3, 0] }} transition={{ duration: 5.5, repeat: Infinity, delay: 1 }} className="px-3 py-1.5 rounded-full bg-white border border-slate-200 shadow-sm text-[11px] font-medium text-slate-600">
              \u25CF Hey Nova
            </motion.div>
          </div>

          {/* main window */}
          <div className="relative rounded-[20px] bg-white border border-slate-200 shadow-[0_16px_48px_rgba(15,23,42,0.08),0_4px_12px_rgba(15,23,42,0.06)] overflow-hidden">
            <div className="h-10 flex items-center justify-between px-4 bg-slate-50/80 border-b border-slate-200">
              <div className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-full bg-[#ff5f56] border border-black/10" />
                <span className="w-3 h-3 rounded-full bg-[#ffbd2e] border border-black/10" />
                <span className="w-3 h-3 rounded-full bg-[#27c93f] border border-black/10" />
              </div>
              <span className="text-[11px] font-medium text-slate-500 tracking-wide">Nova \u2014 voice desktop</span>
              <span className="flex items-center gap-1.5 text-[11px] text-emerald-600 font-medium"><span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" /> Listening</span>
            </div>

            <div className="grid lg:grid-cols-[1.15fr_0.85fr] gap-0">
              {/* left: conversation */}
              <div className="p-5 lg:p-6">
                <div className="space-y-3">
                  <div className="flex gap-3">
                    <span className="w-7 h-7 rounded-full bg-indigo-600 grid place-items-center text-white text-[10px] shrink-0">\u25C9</span>
                    <div className="rounded-2xl rounded-tl-sm bg-slate-900 text-white px-4 py-3 text-[13px] max-w-[85%]">Hey Nova, open Brave and search YouTube for lo-fi</div>
                  </div>
                  <div className="flex gap-3">
                    <span className="w-7 h-7 rounded-full bg-emerald-500 grid place-items-center text-white shrink-0">\u2713</span>
                    <div className="rounded-2xl rounded-tl-sm bg-emerald-50 border border-emerald-200 px-4 py-3 text-[13px] text-emerald-800 max-w-[85%]">Opening Brave... searching YouTube \u00B7 <span className="font-medium">done</span></div>
                  </div>
                  <div className="flex gap-3 opacity-60">
                    <span className="w-7 h-7 rounded-full bg-slate-200 grid place-items-center text-slate-600 text-[10px] shrink-0">\u25C9</span>
                    <div className="rounded-2xl rounded-tl-sm bg-slate-100 border border-slate-200 px-4 py-3 text-[13px] text-slate-600 max-w-[85%]">Play the first one</div>
                  </div>
                </div>

                {/* waveform */}
                <div className="mt-5 flex items-center gap-2 p-3 rounded-xl bg-slate-50 border border-slate-200">
                  <span className="w-8 h-8 rounded-full bg-indigo-600 grid place-items-center text-white"><Mic size={14} /></span>
                  <div className="flex items-center gap-[3px] flex-1">
                    {[10,18,14,28,16,22,12,20,14].map((h,i)=>(
                      <motion.span key={i} animate={{ height: [h*0.5, h, h*0.6] }} transition={{ duration: 0.9, repeat: Infinity, delay: i*0.08 }} className="w-[3px] rounded-full bg-indigo-500" style={{ height: h }} />
                    ))}
                  </div>
                  <span className="text-[11px] font-medium text-slate-500">\u2022 0:42</span>
                </div>
              </div>

              {/* right: NovaOrb custom */}
              <div className="bg-gradient-to-br from-indigo-50 via-white to-violet-50 border-t lg:border-t-0 lg:border-l border-slate-200 p-6 grid place-items-center relative overflow-hidden">
                <div className="absolute inset-0 bg-grid opacity-30" />
                <NovaOrb />
              </div>
            </div>

            {/* bottom bar */}
            <div className="px-4 py-3 bg-slate-50 border-t border-slate-200 flex flex-wrap items-center justify-between gap-3 text-[11px]">
              <span className="text-slate-500">Works in any Windows app \u00B7 Offline wake word</span>
              <span className="flex items-center gap-2">
                <span className="px-2 py-1 rounded-full bg-white border border-slate-200 text-slate-600">Brave</span>
                <span className="px-2 py-1 rounded-full bg-white border border-slate-200 text-slate-600">YouTube</span>
                <span className="px-2 py-1 rounded-full bg-white border border-slate-200 text-slate-600">Notepad</span>
              </span>
            </div>
          </div>
        </motion.div>

        <p className="mt-6 text-center text-[11px] text-slate-400">No video needed \u2014 window is live interactive mock</p>
      </div>
    </section>
  )
}
