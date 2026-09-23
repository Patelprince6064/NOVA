import { useState, useEffect } from 'react'
import { Menu, X } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

const links = [
  { label: 'Home', href: '#home' },
  { label: 'Features', href: '#features' },
  { label: 'How It Works', href: '#how-it-works' },
  { label: 'Use Cases', href: '#use-cases' },
  { label: 'Download', href: '#download' },
  { label: 'Docs', href: '#docs' },
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
    <header
      className={`fixed top-0 inset-x-0 z-50 transition-all duration-300 border-b ${
        scrolled
          ? 'bg-white/90 backdrop-blur-xl border-gray-200 shadow-[0_1px_3px_rgba(0,0,0,0.04),0_4px_12px_rgba(0,0,0,0.04)]'
          : 'bg-white/60 backdrop-blur-[6px] border-transparent'
      }`}
    >
      <nav className="max-w-[1200px] mx-auto px-6 lg:px-8 h-[64px] flex items-center justify-between">
        <a href="#home" className="flex items-center gap-2.5 group">
          <span className="relative w-7 h-7 rounded-full bg-gray-900 flex items-center justify-center overflow-hidden">
            <span  />
            <span className="relative w-2.5 h-2.5 rounded-full bg-white shadow-[0_0_10px_rgba(255,255,255,0.6)]" />
            <span  />
          </span>
          <span className="text-[18px] font-semibold tracking-[-0.02em] text-gray-900">Nova</span>
        </a>

        <div className="hidden md:flex items-center gap-8">
          {links.map(l => (
            <a
              key={l.label}
              href={l.href}
              className="text-[14px] font-medium text-gray-500 hover:text-gray-900 transition-colors"
            >
              {l.label}
            </a>
          ))}
        </div>

        <div className="hidden md:flex items-center">
          <a
            href={import.meta.env.VITE_DOWNLOAD_URL || '#download'}
            className="inline-flex items-center gap-2 h-[36px] px-[18px] rounded-full bg-gray-900 text-white text-[14px] font-medium hover:bg-black transition-colors shadow-sm"
          >
            Get Nova
          </a>
        </div>

        <button
          aria-label="Toggle menu"
          onClick={() => setOpen(!open)}
          className="md:hidden w-9 h-9 grid place-items-center rounded-full border border-gray-200 bg-white text-gray-700"
        >
          {open ? <X size={16} /> : <Menu size={16} />}
        </button>
      </nav>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="md:hidden border-t border-gray-200 bg-white"
          >
            <div className="px-6 py-6 flex flex-col gap-1">
              {links.map(l => (
                <a
                  key={l.label}
                  href={l.href}
                  onClick={() => setOpen(false)}
                  className="py-3 text-[15px] font-medium text-gray-600 hover:text-gray-900 border-b border-gray-100 last:border-0"
                >
                  {l.label}
                </a>
              ))}
              <a
                href={import.meta.env.VITE_DOWNLOAD_URL || '#download'}
                onClick={() => setOpen(false)}
                className="mt-4 inline-flex justify-center items-center h-11 rounded-full bg-gray-900 text-white font-medium"
              >
                Get Nova
              </a>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  )
}
