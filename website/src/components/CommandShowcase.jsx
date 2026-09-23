import { motion } from 'framer-motion'

const cmds = ["Open VS Code","Open YouTube","Search Python tutorials","Scroll down","Go back","Type hello world","What\\u0027s on my screen?","Stop","Try again","Open Brave","Open Notepad","Search Arijit Singh","Play the first one","Go to Google","Refresh"]

export default function CommandShowcase(){
  return (
    <section className="py-10 bg-white">
      <div className="max-w-[1200px] mx-auto px-6 lg:px-8 text-center">
        <h2 className="font-display text-[32px] font-semibold tracking-[-0.03em] text-gray-900">Just talk to Nova.</h2>
        <div className="mt-8 flex flex-wrap justify-center gap-2 lg:gap-3 max-w-[900px] mx-auto">
          {cmds.map((c,i)=>(
            <motion.span
              key={c+i}
              initial={{opacity:0, y:8}}
              whileInView={{opacity:1, y:0}}
              viewport={{once:true}}
              transition={{delay: (i%5)*0.06}}
              whileHover={{y:-2, scale:1.02}}
              className="px-4 py-2 rounded-full bg-white border border-gray-200 text-[13px] font-medium text-gray-600 hover:bg-gray-50 hover:text-gray-900 hover:border-gray-300 transition-colors cursor-default shadow-sm"
            >"{c}"</motion.span>
          ))}
        </div>
      </div>
    </section>
  )
}
