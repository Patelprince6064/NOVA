import { Sparkles } from 'lucide-react'

export default function Footer(){
  const gh = "https://github.com/Patelprince6064/NOVA"
  return (
    <footer className="border-t border-slate-200 py-8 bg-[#F8FAFC]">
      <div className="max-w-[1160px] mx-auto px-4 lg:px-6">
        <div className="flex flex-col lg:flex-row gap-8 justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className="w-7 h-7 rounded-xl bg-indigo-600 grid place-items-center"><Sparkles size={14} className="text-white" /></span>
              <span className="font-semibold text-slate-900">Nova</span>
            </div>
            <p className="mt-2 text-[12px] leading-relaxed text-slate-500 max-w-[260px]">Lightweight Windows voice assistant — hands-free, private, open source.</p>
          </div>
          <div className="flex gap-10 text-[12px]">
            <div>
              <div className="font-semibold text-slate-900 mb-2">Product</div>
              <div className="flex flex-col gap-1.5 text-slate-500">
                <a href="#features" className="hover:text-slate-900">Features</a>
                <a href="#how-it-works" className="hover:text-slate-900">How it works</a>
                <a href="#download" className="hover:text-slate-900">Download</a>
              </div>
            </div>
            <div>
              <div className="font-semibold text-slate-900 mb-2">Resources</div>
              <div className="flex flex-col gap-1.5 text-slate-500">
                <a href={gh} target="_blank" rel="noreferrer" className="hover:text-slate-900">GitHub</a>
                <a href="#commands" className="hover:text-slate-900">Commands</a>
              </div>
            </div>
          </div>
        </div>
        <div className="mt-8 pt-6 border-t border-slate-200 flex flex-col sm:flex-row gap-2 justify-between text-[11px] text-slate-400">
          <span>\u00A9 2026 Nova. Built for everyday Windows use.</span>
          <span>Free \u00B7 Open source \u00B7 MIT</span>
        </div>
      </div>
    </footer>
  )
}
