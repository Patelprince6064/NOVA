import { motion } from 'framer-motion'

const apps = ["Explorer","Word","Excel","Chrome","Brave","VS Code","Notepad","YouTube","Google","Gmail","Slack","Notion","GitHub","Figma","Spotify","Edge","Firefox","Calculator","PowerPoint","Teams"]

export default function UseCases() {
  return (
    <section className="py-12 lg:py-20 bg-[#f5f5f7] border-y border-[#e8e8ed]">
      <div className="max-w-[1160px] mx-auto px-4 lg:px-6">
        <div className="grid lg:grid-cols-[1.1fr_0.9fr] gap-8 items-center">
          <div>
            <p className="text-[11px] font-semibold tracking-[0.16em] text-[#86868b] uppercase">Who this is for</p>
            <h2 className="mt-3 font-display text-[30px] lg:text-[38px] font-semibold tracking-[-0.03em] text-[#1d1d1f] leading-[1.05]">Built for people who<br/>live on Windows.</h2>
            <div className="mt-6 grid grid-cols-3 gap-4 max-w-[420px]">
              <div className="rounded-xl bg-white border border-[#e8e8ed] p-4 text-center">
                <div className="text-[20px] font-semibold text-[#1d1d1f]">150</div>
                <div className="text-[10px] tracking-[0.08em] uppercase text-[#86868b]">wpm voice</div>
                <div className="mt-2 h-1.5 rounded-full bg-[#e8e8ed] overflow-hidden"><div className="h-full w-[85%] bg-[#1d1d1f]" /></div>
              </div>
              <div className="rounded-xl bg-white border border-[#e8e8ed] p-4 text-center">
                <div className="text-[20px] font-semibold text-[#1d1d1f]">45</div>
                <div className="text-[10px] tracking-[0.08em] uppercase text-[#86868b]">wpm hands</div>
                <div className="mt-2 h-1.5 rounded-full bg-[#e8e8ed] overflow-hidden"><div className="h-full w-[30%] bg-[#6e6e73]" /></div>
              </div>
              <div className="rounded-xl bg-white border border-[#e8e8ed] p-4 text-center">
                <div className="text-[14px] font-semibold text-[#1d1d1f]">95%+</div>
                <div className="text-[10px] tracking-[0.08em] uppercase text-[#86868b]">accuracy</div>
                <div className="mt-2 text-[11px] text-[#6e6e73]">on-device</div>
              </div>
            </div>
            <p className="mt-4 text-[12px] text-[#86868b]">Any app where you can type, Nova can type for you.</p>
          </div>
          <div className="rounded-[20px] bg-white border border-[#e8e8ed] p-6 window-shadow">
            <div className="text-[11px] font-semibold tracking-[0.12em] text-[#86868b] uppercase">Apps it drives by voice</div>
            <div className="mt-4 relative overflow-hidden mask-marquee">
              <div className="flex w-max animate-marquee gap-6">
                {[...apps, ...apps].map((a,i)=>(
                  <span key={a+i} className="inline-flex items-center gap-2 text-[13px] font-medium text-[#424245] whitespace-nowrap">
                    <span className="w-1 h-1 rounded-full bg-[#d2d2d7]" />{a}
                  </span>
                ))}
              </div>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-2">
              {["Open apps & files","Control browser","Type & navigate","Screen understanding"].map(t=>(
                <span key={t} className="px-3 py-2 rounded-full bg-[#f5f5f7] border border-[#e8e8ed] text-[11px] font-medium text-[#424245] text-center">{t}</span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
