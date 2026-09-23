import { motion } from 'framer-motion'

export default function PrivacySection(){
  return (
    <section className="py-16 lg:py-20 bg-white">
      <div className="max-w-[1160px] mx-auto px-4 lg:px-6">
        <div className="text-center max-w-[640px] mx-auto">
          <h2 className="font-display text-[28px] lg:text-[36px] font-semibold tracking-[-0.03em] text-[#1d1d1f]">The mic is on. Nova isn\u2019t.</h2>
          <p className="mt-3 text-[14px] leading-relaxed text-[#6e6e73]">Until you say the trigger word, all that runs is a tiny listener on your own computer. It can\u2019t record, store, or send a thing. It just waits.</p>
        </div>
        <div className="mt-10 grid md:grid-cols-3 gap-4 lg:gap-6 relative">
          <div className="hidden md:block absolute top-[28px] left-[18%] right-[18%] h-[1px] border-t border-dashed border-[#d2d2d7]" />
          {[
            { title: "Waiting", desc: "A tiny on-device model listens for \u201Chey Nova\u201D, and nothing else.", icon: "\u25CB", delay: 0 },
            { title: "Awake", desc: "Now it hears you. Your voice is transcribed right on your own computer.", icon: "\u25C9", delay: 0.08, active: true },
            { title: "Back to waiting", desc: "Nothing stored, nothing leaves. The mic goes back to sleep.", icon: "\u21BB", delay: 0.16 },
          ].map(s=>(
            <motion.div key={s.title} initial={{opacity:0,y:14}} whileInView={{opacity:1,y:0}} viewport={{once:true}} transition={{delay:s.delay}} className={"relative rounded-[20px] p-6 text-center " + (s.active ? "bg-[#1d1d1f] text-white" : "bg-[#f5f5f7] border border-[#e8e8ed]")}>
              <div className={"mx-auto w-12 h-12 rounded-full grid place-items-center text-[16px] " + (s.active ? "bg-white text-[#1d1d1f]" : "bg-white border border-[#e8e8ed] text-[#424245]")}>{s.icon}</div>
              <h3 className={"mt-4 text-[14px] font-semibold " + (s.active ? "text-white" : "text-[#1d1d1f]")}>{s.title}</h3>
              <p className={"mt-2 text-[12px] leading-relaxed " + (s.active ? "text-white/60" : "text-[#6e6e73]")}>{s.desc}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
