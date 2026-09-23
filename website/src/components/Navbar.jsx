import { useState, useEffect } from 'react'
import { Menu, X, Sparkles } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

const links = [
  { label: 'Features', href: '#features' },
  { label: 'How it works', href: '#how-it-works' },
  { label: 'Commands', href: '#commands' },
  { label: 'Download', href: '#download' },
]

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false)
  const [open, setOpen] = useState(false)
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])
  return (
    <header
      className={
        "fixed top-0 inset-x-0 z-50 transition-all duration-300 " +
        (scrolled
          ? "bg-white/80 backdrop-blur-[14px] border-b border-slate-200/70 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_4px_16px_rgba(15,23,42,0.04)]"
          : "bg-[#FCFCF9] border-b border-transparent")
      }
    >
      <nav className="max-w-[1240px] mx-auto px-6 lg:px-8 h-[64px] flex items-center justify-between">
        {/* left: logo */}
        <a href="#home" className="flex items-center gap-2.5 group shrink-0">
          <span className="relative w-[32px] h-[32px] rounded-[10px] bg-gradient-to-br from-indigo-600 to-violet-600 grid place-items-center shadow-[0_2px_8px_rgba(79,70,229,0.25),0_1px_2px_rgba(79,70,229,0.2)] ring-1 ring-black/5 group-hover:shadow-[0_4px_12px_rgba(79,70,229,0.3)] transition-shadow">
            <Sparkles size={16} className="text-white" strokeWidth={2} />
          </span>
          <span className="text-[18px] font-semibold tracking-[-0.02em] text-slate-900 leading-none">Nova</span>
          <span className="hidden sm:inline-flex items-center ml-1 px-[7px] h-[20px] rounded-full bg-[#EEF2FF] border border-[#C7D2FE] text-[10px] font-bold tracking-[0.08em] text-[#4F46E5] leading-none">
            BETA
          </span>
        </a>

        {/* center: links - perfectly centered */}
        <div className="hidden md:flex items-center gap-8 absolute left-1/2 -translate-x-1/2">
          {links.map(l => (
            <a
              key={l.label}
              href={l.href}
              className="relative text-[14px] font-[450] text-slate-500 hover:text-slate-900 transition-colors duration-150 py-1 group"
            >
              {l.label}
              <span className="absolute -bottom-1 left-0 w-0 h-[1.5px] bg-indigo-600 group-hover:w-full transition-all duration-200" />
            </a>
          ))}
        </div>

        {/* right: actions */}
        <div className="hidden md:flex items-center gap-2.5 shrink-0">
          <a
            href="https://github.com/Patelprince6064/NOVA"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center justify-center h-[36px] px-[18px] rounded-full bg-white border border-slate-200 text-[14px] font-medium text-slate-700 hover:bg-slate-50 hover:border-slate-300 hover:text-slate-900 shadow-sm transition-all"
          >
            GitHub
          </a>
          <a
            href="#download"
            className="inline-flex items-center justify-center h-[36px] px-[20px] rounded-full bg-[#4F46E5] text-white text-[14px] font-semibold hover:bg-[#4338CA] hover:shadow-[0_8px_20px_rgba(79,70,229,0.25)] hover:-translate-y-[0.5px] active:translate-y-0 shadow-[0_2px_8px_rgba(79,70,229,0.2)] transition-all"
          >
            Download
          </a>
        </div>

        {/* mobile */}
        <button
          aria-label="Toggle menu"
          onClick={() => setOpen(!open)}
          className="md:hidden w-9 h-9 grid place-items-center rounded-xl bg-white border border-slate-200 text-slate-700 shadow-sm hover:bg-slate-50 transition-colors"
        >
          {open ? <X size={16} /> : <Menu size={16} />}
        </button>
      </nav>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.18 }}
            className="md:hidden border-t border-slate-200 bg-white/95 backdrop-blur-xl"
          >
            <div className="px-6 py-5 flex flex-col">
              {links.map(l => (
                <a
                  key={l.label}
                  href={l.href}
                  onClick={() => setOpen(false)}
                  className="py-3 text-[15px] font-medium text-slate-700 hover:text-slate-900 border-b border-slate-100 last:border-0 transition-colors"
                >
                  {l.label}
                </a>
              ))}
              <div className="mt-4 grid grid-cols-2 gap-3">
                <a
                  href="https://github.com/Patelprince6064/NOVA"
                  target="_blank"
                  rel="noreferrer"
                  onClick={() => setOpen(false)}
                  className="h-11 grid place-items-center rounded-full bg-white border border-slate-200 text-slate-700 font-medium hover:bg-slate-50"
                >
                  GitHub
                </a>
                <a
                  href="#download"
                  onClick={() => setOpen(false)}
                  className="h-11 grid place-items-center rounded-full bg-indigo-600 text-white font-semibold hover:bg-indigo-700 shadow-sm"
                >
                  Download
                </a>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  )
}
