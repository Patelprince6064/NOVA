import { Download, ExternalLink } from 'lucide-react'

export default function DownloadCTA(){
  const dl = import.meta.env.VITE_DOWNLOAD_URL
  const gh = import.meta.env.VITE_GITHUB_URL || "https://github.com/Patelprince6064/NOVA"
  return (
    <section id="download" className="py-12 lg:py-20">
      <div className="max-w-[1200px] mx-auto px-6 lg:px-8">
        <div className="relative overflow-hidden rounded-[28px] bg-gradient-to-br from-[#0E1A3A] via-[#0B1226] to-[#05070B] border border-white/[0.08] p-8 lg:p-12">
          <div className="absolute -top-20 -right-20 w-[500px] h-[500px] bg-blue-600/15 blur-3xl rounded-full" />
          <div className="absolute -bottom-32 -left-32 w-[400px] h-[400px] bg-blue-500/10 blur-3xl rounded-full" />
          <div className="relative flex flex-col lg:flex-row lg:items-center justify-between gap-8">
            <div>
              <h2 className="font-display text-[32px] lg:text-[40px] font-semibold tracking-[-0.03em] text-white leading-[1.05]">Your smarter,<br/>hands-free PC experience<br/>starts here.</h2>
              <p className="mt-4 text-[13px] text-white/40">Free • Open source • Built for everyday use</p>
            </div>
            <div className="flex flex-wrap gap-3 shrink-0">
              {dl ? (
                <a href={dl} className="inline-flex items-center gap-2 h-[46px] px-6 rounded-full bg-white text-[#05070B] font-medium hover:bg-white/90 transition-colors">
                  <Download size={16}/> Download for Windows
                </a>
              ) : (
                <span className="inline-flex items-center gap-2 h-[46px] px-6 rounded-full bg-white/10 border border-white/20 text-white/50 text-[14px]">Download coming soon</span>
              )}
              <a href={gh} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 h-[46px] px-6 rounded-full bg-white/[0.06] border border-white/10 text-white font-medium hover:bg-white/10 transition-colors">
                <ExternalLink size={16}/> View on GitHub
              </a>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
