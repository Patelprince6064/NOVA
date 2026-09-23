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
              <span className="w-8 h-8 rounded-full bg-gray-900 grid place-items-center text-white text-[11px]">🎙</span>
              <span className="text-gray-900 font-medium">Hey Nova, open Brave.</span>
            </div>
            <div className="mt-6 rounded-xl bg-gray-50 border border-gray-200 p-4">
              <p className="text-gray-600 text-[13px]">Opening Brave...</p>
              <p className="text-emerald-600 text-[13px] mt-2">✓ Brave is ready.</p>
            </div>
            <div className="mt-4 text-center text-[12px] text-gray-400">Simulated demo — no video required</div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

export default function App() {
  const [demo, setDemo] = useState(false)
  return (
    <div className="min-h-screen bg-white text-gray-900 selection:bg-gray-900/10">
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
