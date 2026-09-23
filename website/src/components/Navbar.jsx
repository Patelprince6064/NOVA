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
    const onScroll = () => setScrolled(window.scrollY > 10)
    window.addEventListener('scroll', onScroll)
    return () => window.removeEventListener('scroll', onScroll)
  }, [])
  return (
    <header className={"fixed top-0 inset-x-0 z-50 border-b " + (scrolled ? "bg-white/85 backdrop-blur-xl border-slate-200 shadow-sm" : "bg-[#FCFCF9]/60 backdrop-blur-md border-transparent")}>
      <nav className="max-w-[1160px] mx-auto px-4 lg:px-6 h-[60px] flex items-center justify-between">
        <a href="#home" className="flex items-center gap-2.5">
          <span className="w-8 h-8 rounded-xl bg-indigo-600 grid place-items-center shadow-[0_4px_12px_rgba(79,70,229,0.25)]">
            <Sparkles size={16} className="text-white" />
          </span>
          <span className="text-[17px] font-semibold tracking-[-0.02em] text-slate-900">Nova</span>
          <span className="hidden sm:inline-flex ml-1 px-2 py-0.5 rounded-full bg-indigo-50 border border-indigo-200 text-[10px] font-semibold tracking-[0.08em] text-indigo-700">BETA</span>
        </a>
        <div className="hidden md:flex items-center gap-7">
          {links.map(l => (
            <a key={l.label} href={l.href} className="text-[13px] font-medium text-slate-500 hover:text-slate-900 transition-colors">{l.label}</a>
          ))}
        </div>
        <div className="hidden md:flex items-center gap-2">
          <a href="https://github.com/Patelprince6064/NOVA" target="_blank" rel="noreferrer" className="h-8 px-3 rounded-full bg-white border border-slate-200 text-[13px] font-medium text-slate-700 hover:bg-slate-50">GitHub</a>
          <a href="#download" className="h-8 px-4 rounded-full bg-indigo-600 text-white text-[13px] font-medium hover:bg-indigo-700 shadow-sm">Download</a>
        </div>
        <button onClick={() => setOpen(!open)} className="md:hidden w-9 h-9 grid place-items-center rounded-xl border border-slate-200 bg-white text-slate-700">
          {open ? <X size={16} /> : <Menu size={16} />}
        </button>
      </nav>
      <AnimatePresence>
        {open && (
          <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} className="md:hidden border-t border-slate-200 bg-white">
            <div className="px-4 py-4 flex flex-col gap-1">
              {links.map(l => (
                <a key={l.label} href={l.href} onClick={() => setOpen(false)} className="py-2.5 text-[14px] font-medium text-slate-600 hover:text-slate-900 border-b border-slate-100 last:border-0">{l.label}</a>
              ))}
              <a href="#download" onClick={() => setOpen(false)} className="mt-2 h-10 grid place-items-center rounded-full bg-indigo-600 text-white font-medium">Download for Windows</a>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  )
}
