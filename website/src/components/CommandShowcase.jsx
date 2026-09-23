import { useState } from 'react'
import { ChevronDown } from 'lucide-react'

const faqs = [
  { q: "Is Nova a voice typing app?", a: "Yes — and more. Nova is hands-free voice control for Windows. Speak and it types, opens apps, navigates browser, and checks your screen. No keyboard needed for everyday tasks." },
  { q: "Do I really never touch the keyboard?", a: "For voice work, no. Say \u201CHey Nova\u201D then speak. Prefer a key? Manual mode (press Enter to speak) is also available." },
  { q: "Is it always listening to me?", a: "No. A tiny on-device Vosk model waits for \u201Chey nova\u201D. Nothing is recorded or sent until the trigger. After the command, it goes back to sleep." },
  { q: "Which apps does it work with?", a: "Every Windows app where you can type or click: Explorer, Office, Chrome/Brave, VS Code, YouTube, Gmail, Slack, Notion, and more via browser automation." },
  { q: "How accurate is transcription?", a: "95%+ for clear speech via faster-whisper (base model, on-device). Handles accents and noise well; you can choose tiny/base/small." },
  { q: "Do I need internet?", a: "No for core features: wake word, STT, TTS, PC control run on-device. AI and vision need an API key and internet, but local commands work offline." },
  { q: "What happens after download?", a: "Install Python 3.11+, pip install -r requirements.txt, setup_browser.bat (optional), copy .env.example to .env, then python run.py. Free, no card." },
  { q: "Which computers does it run on?", a: "Windows 10/11 64-bit, microphone + speakers, Python 3.11+. 4 cores / 8GB recommended for Whisper base. Works on most recent laptops." },
]

export default function CommandShowcase(){
  const [open, setOpen] = useState(0)
  return (
    <section className="py-12 lg:py-20 bg-[#f5f5f7] border-y border-[#e8e8ed]">
      <div className="max-w-[760px] mx-auto px-4 lg:px-6">
        <h2 className="font-display text-[26px] lg:text-[32px] font-semibold tracking-[-0.03em] text-[#1d1d1f] text-center">Questions, answered.</h2>
        <div className="mt-8 rounded-[16px] bg-white border border-[#e8e8ed] divide-y divide-[#e8e8ed] overflow-hidden">
          {faqs.map((f,i)=>(
            <div key={f.q}>
              <button onClick={()=> setOpen(open===i ? -1 : i)} className="w-full flex items-center justify-between gap-4 px-5 py-4 text-left hover:bg-[#f5f5f7]/50 transition-colors">
                <span className="text-[13px] lg:text-[14px] font-medium text-[#1d1d1f]">{f.q}</span>
                <ChevronDown size={16} className={"shrink-0 text-[#86868b] transition-transform " + (open===i ? "rotate-180" : "")} />
              </button>
              {open===i && <div className="px-5 pb-4 text-[13px] leading-relaxed text-[#6e6e73]">{f.a}</div>}
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
