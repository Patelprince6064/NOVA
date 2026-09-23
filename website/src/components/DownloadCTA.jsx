import { Check, Download } from 'lucide-react'

export default function DownloadCTA(){
  const dl = import.meta.env.VITE_DOWNLOAD_URL
  return (
    <section id="download" className="py-12 lg:py-20 bg-white">
      <div className="max-w-[960px] mx-auto px-4 lg:px-6">
        <div className="text-center">
          <h2 className="font-display text-[28px] lg:text-[36px] font-semibold tracking-[-0.03em] text-[#1d1d1f]">Pricing</h2>
          <p className="mt-2 text-[13px] text-[#6e6e73]">Free to try and see how it works. Get the full version when you are ready.</p>
        </div>
        <div className="mt-8 grid md:grid-cols-2 gap-4 max-w-[720px] mx-auto">
          <div className="rounded-[20px] bg-white border border-[#e8e8ed] p-6">
            <div className="inline-flex px-2.5 py-1 rounded-full bg-[#f5f5f7] border border-[#e8e8ed] text-[10px] font-semibold tracking-[0.12em] uppercase text-[#6e6e73]">Free trial</div>
            <div className="mt-3 flex items-baseline gap-2"><span className="text-[28px] font-semibold text-[#1d1d1f]">Free</span><span className="text-[12px] text-[#86868b]">no card required</span></div>
            <ul className="mt-4 space-y-2 text-[13px] text-[#424245]">
              {["2,000 words included","50 commands","Hands-free and manual","Runs on your PC"].map(t=>(
                <li key={t} className="flex items-center gap-2"><span className="w-5 h-5 rounded-full bg-[#f5f5f7] border border-[#e8e8ed] grid place-items-center"><Check size={12} className="text-[#1d1d1f]"/></span>{t}</li>
              ))}
            </ul>
            <a href={dl || "#how-it-works"} className="mt-6 flex items-center justify-center h-10 rounded-full bg-white border border-[#d2d2d7] text-[#1d1d1f] text-[13px] font-medium hover:bg-[#f5f5f7]">Try for free</a>
          </div>
          <div className="rounded-[20px] bg-[#1d1d1f] border border-[#1d1d1f] p-6 text-white relative overflow-hidden">
            <div className="inline-flex px-2.5 py-1 rounded-full bg-white text-[#1d1d1f] text-[10px] font-semibold tracking-[0.12em] uppercase">Unlimited</div>
            <div className="mt-3 flex items-baseline gap-2"><span className="text-[28px] font-semibold">Free</span><span className="text-[12px] text-white/60">open source</span></div>
            <p className="mt-1 text-[12px] text-white/60">Nova is free and open source. No subscription.</p>
            <ul className="mt-4 space-y-2 text-[13px] text-white/90">
              {["Unlimited words","Unlimited commands","Hands-free and manual","Runs on your PC"].map(t=>(
                <li key={t} className="flex items-center gap-2"><span className="w-5 h-5 rounded-full bg-white/10 border border-white/20 grid place-items-center"><Check size={12} className="text-white"/></span>{t}</li>
              ))}
            </ul>
            <a href={dl || "https://github.com/Patelprince6064/NOVA"} target="_blank" rel="noreferrer" className="mt-6 flex items-center justify-center gap-2 h-10 rounded-full bg-white text-[#1d1d1f] text-[13px] font-medium hover:bg-white/90"><Download size={14}/> Download for Windows</a>
            <div className="mt-3 text-center text-[11px] text-white/50">Windows 10/11 \u00B7 4 cores 8GB \u00B7 Mic required</div>
          </div>
        </div>
      </div>
    </section>
  )
}
