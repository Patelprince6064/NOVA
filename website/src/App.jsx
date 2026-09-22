import { useState } from 'react'
import Navbar from './components/Navbar'
import Hero from './components/Hero'
import FeatureGrid from './components/FeatureGrid'
import VoiceDemo from './components/VoiceDemo'
import HowItWorks from './components/HowItWorks'
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
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 z-[100] grid place-items-center p-4 bg-black/60 backdrop-blur-sm" onClick={onClose}>
          <motion.div
            initial={{ scale: 0.96, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.96, opacity: 0 }}
            onClick={e => e.stopPropagation()}
            className="w-full max-w-[560px] rounded-[24px] bg-[#0B0D14] border border-white/10 p-6 relative"
          >
            <button onClick={onClose} className="absolute top-4 right-4 w-8 h-8 grid place-items-center rounded-full bg-white/10 text-white/70 hover:text-white"><X size={14} /></button>
            <div className="flex items-center gap-3">
              <span className="w-8 h-8 rounded-full bg-white/10 grid place-items-center">🎙</span>
              <span className="text-white font-medium">Hey Nova, open Brave.</span>
            </div>
            <div className="mt-6 rounded-xl bg-white/[0.04] border border-white/10 p-4">
              <p className="text-white/60 text-[13px]">Opening Brave...</p>
              <p className="text-emerald-400 text-[13px] mt-2">✓ Brave is ready.</p>
            </div>
            <div className="mt-4 text-center text-[12px] text-white/30">Simulated demo — no video required</div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

export default function App() {
  const [demo, setDemo] = useState(false)
  return (
    <div className="min-h-screen bg-[#05070B] text-white selection:bg-blue-500/30">
      <div className="bg-grid fixed inset-0 pointer-events-none" />
      <Navbar />
      <main>
        <Hero onDemo={() => setDemo(true)} />
        <FeatureGrid />
        <VoiceDemo />
        <HowItWorks />
        <UseCases />
        <WorkflowDemo />
        <PrivacySection />
        <PerformanceSection />
        <CommandShowcase />
        <DownloadCTA />
      </main>
      <Footer />
      <DemoModal open={demo} onClose={() => setDemo(false)} />
    </div>
  )
}
