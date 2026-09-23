import { useState } from 'react'
import Navbar from './components/Navbar'
import Hero from './components/Hero'
import FeatureGrid from './components/FeatureGrid'
import HowItWorks from './components/HowItWorks'
import VoiceDemo from './components/VoiceDemo'
import UseCases from './components/UseCases'
import WorkflowDemo from './components/WorkflowDemo'
import PrivacySection from './components/PrivacySection'
import PerformanceSection from './components/PerformanceSection'
import CommandShowcase from './components/CommandShowcase'
import DownloadCTA from './components/DownloadCTA'
import Footer from './components/Footer'
import { motion, AnimatePresence } from 'framer-motion'
import { X } from 'lucide-react'

function DemoModal({ open, onClose }) {
  return (
    <AnimatePresence>
      {open && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 z-[100] grid place-items-center p-4 bg-black/40 backdrop-blur-sm" onClick={onClose}>
          <motion.div
            initial={{ scale: 0.96, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.96, opacity: 0 }}
            onClick={e => e.stopPropagation()}
            className="w-full max-w-[560px] rounded-[24px] bg-white border border-gray-200 p-6 relative shadow-[0_16px_48px_rgba(0,0,0,0.12)]"
          >
            <button onClick={onClose} className="absolute top-4 right-4 w-8 h-8 grid place-items-center rounded-full bg-gray-100 text-gray-500 hover:text-gray-900 hover:bg-gray-200 transition-colors"><X size={14} /></button>
            <div className="flex items-center gap-3">
              <span className="w-8 h-8 rounded-full bg-gray-900 grid place-items-center text-white text-[11px]">\u25C9</span>
              <span className="text-gray-900 font-medium">Hey Nova, open Brave.</span>
            </div>
            <div className="mt-6 rounded-xl bg-gray-50 border border-gray-200 p-4">
              <p className="text-gray-600 text-[13px]">Opening Brave...</p>
              <p className="text-emerald-600 text-[13px] mt-2">\u2713 Brave is ready.</p>
            </div>
            <div className="mt-4 text-center text-[12px] text-gray-400">Simulated demo \u2014 no video required</div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

function FinalCTA() {
  return (
    <section className="py-20 lg:py-32 text-center" style={{ background: 'var(--v3-final-grad)' }}>
      <div className="max-w-[720px] mx-auto px-4">
        <h2 className="font-display text-[36px] lg:text-[56px] font-semibold tracking-[-0.04em] text-[#1d1d1f] leading-[0.95]">Say the word.</h2>
        <div className="mt-6 flex justify-center">
          <svg width="72" height="58" viewBox="0 0 82 66" fill="none" className="text-[#1d1d1f]/15">
            <polyline points="22,72 50,32 78,72" stroke="currentColor" strokeWidth="3" fill="none" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
        <div className="mt-6 flex justify-center gap-3">
          <a href="#download" className="inline-flex items-center justify-center h-11 px-7 rounded-full bg-[#1d1d1f] text-white text-[14px] font-medium hover:bg-black transition-colors">Try for free</a>
          <a href="https://github.com/Patelprince6064/NOVA" target="_blank" rel="noreferrer" className="inline-flex items-center justify-center h-11 px-6 rounded-full bg-white border border-[#d2d2d7] text-[#1d1d1f] text-[14px] font-medium hover:bg-[#f5f5f7]">View on GitHub</a>
        </div>
        <p className="mt-4 text-[12px] text-[#86868b]">Free \u00B7 Open source \u00B7 Windows 10/11</p>
      </div>
    </section>
  )
}

export default function App() {
  const [demo, setDemo] = useState(false)
  return (
    <div className="min-h-screen bg-white text-gray-900 selection:bg-gray-900/10" data-v3-theme="light">
      <div className="bg-grid fixed inset-0 pointer-events-none opacity-40" />
      <Navbar />
      <main>
        <Hero onDemo={() => setDemo(true)} />
        <FeatureGrid />
        <HowItWorks />
        <VoiceDemo />
        <UseCases />
        <WorkflowDemo />
        <PrivacySection />
        <PerformanceSection />
        <CommandShowcase />
        <DownloadCTA />
        <FinalCTA />
      </main>
      <Footer />
      <DemoModal open={demo} onClose={() => setDemo(false)} />
    </div>
  )
}
