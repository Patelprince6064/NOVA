export default function PrivacySection(){
  return (
    <section className="py-14 lg:py-20 bg-white">
      <div className="max-w-[1200px] mx-auto px-6 lg:px-8">
        <div className="rounded-[28px] bg-gray-900 border border-gray-800 p-8 lg:p-12 relative overflow-hidden">
          <div className="absolute -top-32 -right-32 w-[400px] h-[400px] bg-white/5 blur-3xl rounded-full" />
          <div className="relative grid lg:grid-cols-[1.1fr_0.9fr] gap-8 items-center">
            <div>
              <h2 className="font-display text-[32px] lg:text-[40px] font-semibold tracking-[-0.03em] text-white leading-[1.05]">Your computer.<br/>Your control.</h2>
              <p className="mt-4 text-[14px] leading-relaxed text-white/60 max-w-[420px]">Nova is designed to keep everyday interaction simple, transparent, and controlled.</p>
            </div>
            <ul className="space-y-3">
              {[
                "Local speech processing",
                "No unnecessary screen capture",
                "Controlled actions",
                "No arbitrary code execution",
                "Temporary conversation context",
              ].map(t=>(
                <li key={t} className="flex items-center gap-3 text-[14px] text-white/80">
                  <span className="w-6 h-6 rounded-full bg-emerald-500/20 border border-emerald-500/20 grid place-items-center text-emerald-400 text-[12px]">\u2713</span>
                  {t}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  )
}
