import { motion } from 'framer-motion'

const cmds = ["Open VS Code","Open YouTube","Search Python tutorials","Scroll down","Go back","Type hello world","What's on my screen?","Stop","Try again","Open Brave","Open Notepad","Search Arijit Singh","Play the first one","Go to Google","Refresh"]

export default function CommandShowcase(){
  return (
    <section className="py-10">
      <div className="max-w-[1200px] mx-auto px-6 lg:px-8 text-center">
        <h2 className="font-display text-[32px] font-semibold tracking-[-0.03em] text-white">Just talk to Nova.</h2>
        <div className="mt-8 flex flex-wrap justify-center gap-2 lg:gap-3 max-w-[900px] mx-auto">
          {cmds.map((c,i)=>(
            <motion.span
              key={c+i}
              initial={{opacity:0, y:8}}
              whileInView={{opacity:1, y:0}}
              viewport={{once:true}}
              transition={{delay: (i%5)*0.06}}
              whileHover={{y:-2, scale:1.02}}
              className="px-4 py-2 rounded-full bg-white/[0.04] border border-white/[0.06] text-[13px] font-medium text-white/70 hover:bg-white/[0.07] hover:text-white hover:border-white/10 transition-colors cursor-default"
            >"{c}"</motion.span>
          ))}
        </div>
      </div>
    </section>
  )
}
