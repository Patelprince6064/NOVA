import { Shield, Eye, Lock } from 'lucide-react'

export default function PrivacySection(){
  return (
    <section className="py-12 lg:py-16 bg-white">
      <div className="max-w-[1160px] mx-auto px-4 lg:px-6">
        <div className="rounded-[24px] bg-slate-900 border border-slate-800 p-6 lg:p-10 relative overflow-hidden">
          <div className="absolute -top-20 -right-20 w-[420px] h-[420px] bg-indigo-600/20 blur-3xl rounded-full" />
          <div className="absolute -bottom-20 -left-20 w-[380px] h-[380px] bg-violet-600/10 blur-3xl rounded-full" />
          <div className="relative grid lg:grid-cols-[1.1fr_0.9fr] gap-8 items-center">
            <div>
              <p className="inline-flex px-2.5 py-1 rounded-full bg-white/10 border border-white/10 text-[11px] font-semibold tracking-[0.08em] text-white/80 uppercase">Privacy</p>
              <h2 className="mt-3 font-display text-[26px] lg:text-[32px] font-semibold tracking-[-0.03em] text-white leading-[1.1]">Your PC.<br/>Your control.</h2>
              <p className="mt-3 text-[13px] leading-relaxed text-white/60 max-w-[400px]">Local-first where it matters. No background recording, no hidden uploads.</p>
            </div>
            <div className="grid gap-3">
              {[
                { icon: Shield, t: 'Local wake word', d: 'Vosk tiny model \u00B7 RAM only' },
                { icon: Eye, t: 'Screen on demand', d: 'Screenshot only when you ask' },
                { icon: Lock, t: 'Allowlisted', d: 'No shell, no code, validated plans' },
              ].map(r=>(
                <div key={r.t} className="flex items-center gap-3 p-3 rounded-xl bg-white/5 border border-white/10">
                  <span className="w-9 h-9 rounded-xl bg-white/10 grid place-items-center text-white"><r.icon size={16} /></span>
                  <div><div className="text-[13px] font-medium text-white">{r.t}</div><div className="text-[11px] text-white/50">{r.d}</div></div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
