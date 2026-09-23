import { Download, ExternalLink, ArrowRight } from 'lucide-react'

export default function DownloadCTA(){
  const dl = import.meta.env.VITE_DOWNLOAD_URL
  return (
    <section id="download" className="py-12 lg:py-16 bg-white">
      <div className="max-w-[1160px] mx-auto px-4 lg:px-6">
        <div className="relative overflow-hidden rounded-[24px] bg-slate-900 border border-slate-800 p-6 lg:p-10">
          <div className="absolute -top-24 -right-24 w-[520px] h-[520px] bg-indigo-600/20 blur-3xl rounded-full" />
          <div className="absolute -bottom-24 -left-24 w-[420px] h-[420px] bg-violet-600/15 blur-3xl rounded-full" />
          <div className="absolute inset-0 bg-grid opacity-[0.04]" />
          <div className="relative flex flex-col lg:flex-row lg:items-center justify-between gap-6">
            <div>
              <h2 className="font-display text-[26px] lg:text-[34px] font-semibold tracking-[-0.03em] text-white leading-[1.05]">Start hands-free today.</h2>
              <p className="mt-2 text-[13px] text-white/60">Free \u00B7 Open source \u00B7 Runs on your machine \u00B7 No account needed</p>
              <div className="mt-3 flex flex-wrap gap-2 text-[11px]">
                <span className="px-2.5 py-1 rounded-full bg-white/10 border border-white/10 text-white/80">Windows 10/11</span>
                <span className="px-2.5 py-1 rounded-full bg-white/10 border border-white/10 text-white/80">4 cores 8GB</span>
                <span className="px-2.5 py-1 rounded-full bg-white/10 border border-white/10 text-white/80">Mic required</span>
              </div>
            </div>
            <div className="flex flex-wrap gap-3 shrink-0">
              <a href={dl || "#"} className="inline-flex items-center gap-2 h-11 px-6 rounded-full bg-white text-slate-900 font-medium text-[14px] hover:bg-slate-100 transition-colors">
                <Download size={16} /> Download for Windows <ArrowRight size={14} />
              </a>
              <a href="https://github.com/Patelprince6064/NOVA" target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 h-11 px-6 rounded-full bg-white/10 border border-white/20 text-white font-medium text-[14px] hover:bg-white/15">
                <ExternalLink size={16} /> GitHub
              </a>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
