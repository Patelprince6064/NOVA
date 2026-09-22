export default function Footer(){
  const gh = import.meta.env.VITE_GITHUB_URL || "https://github.com/Patelprince6064/NOVA"
  const docs = import.meta.env.VITE_DOCS_URL || gh
  return (
    <footer className="border-t border-white/[0.06] py-10">
      <div className="max-w-[1200px] mx-auto px-6 lg:px-8">
        <div className="flex flex-col lg:flex-row gap-10 justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className="w-6 h-6 rounded-full bg-white/10 border border-white/10 grid place-items-center"><span className="w-2.5 h-2.5 rounded-full bg-white shadow-[0_0_8px_white]"/></span>
              <span className="font-semibold text-white">Nova</span>
            </div>
            <p className="mt-3 text-[13px] leading-relaxed text-white/40 max-w-[280px]">A smarter way to use your computer.</p>
          </div>
          <div className="flex gap-12 text-[13px]">
            <div>
              <div className="font-semibold text-white mb-3">Product</div>
              <div className="flex flex-col gap-2 text-white/50">
                <a href="#home" className="hover:text-white">Home</a>
                <a href="#features" className="hover:text-white">Features</a>
                <a href="#download" className="hover:text-white">Download</a>
              </div>
            </div>
            <div>
              <div className="font-semibold text-white mb-3">Resources</div>
              <div className="flex flex-col gap-2 text-white/50">
                <a href={docs} target="_blank" rel="noreferrer" className="hover:text-white">Docs</a>
                <a href={gh} target="_blank" rel="noreferrer" className="hover:text-white">GitHub</a>
              </div>
            </div>
            <div>
              <div className="font-semibold text-white mb-3">Connect</div>
              <div className="flex flex-col gap-2 text-white/50">
                <a href={gh} target="_blank" rel="noreferrer" className="hover:text-white">GitHub</a>
              </div>
            </div>
          </div>
        </div>
        <div className="mt-10 pt-6 border-t border-white/[0.06] text-[12px] text-white/30">© 2026 Nova. Built for everyday use.</div>
      </div>
    </footer>
  )
}
