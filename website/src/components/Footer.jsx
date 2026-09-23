export default function Footer(){
  const gh = import.meta.env.VITE_GITHUB_URL || "https://github.com/Patelprince6064/NOVA"
  const docs = import.meta.env.VITE_DOCS_URL || gh
  return (
    <footer className="border-t border-gray-200 py-10 bg-gray-50/50">
      <div className="max-w-[1200px] mx-auto px-6 lg:px-8">
        <div className="flex flex-col lg:flex-row gap-10 justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className="w-6 h-6 rounded-full bg-gray-900 grid place-items-center"><span className="w-2.5 h-2.5 rounded-full bg-white"/></span>
              <span className="font-semibold text-gray-900">Nova</span>
            </div>
            <p className="mt-3 text-[13px] leading-relaxed text-gray-500 max-w-[280px]">A smarter way to use your computer.</p>
          </div>
          <div className="flex gap-12 text-[13px]">
            <div>
              <div className="font-semibold text-gray-900 mb-3">Product</div>
              <div className="flex flex-col gap-2 text-gray-500">
                <a href="#home" className="hover:text-gray-900">Home</a>
                <a href="#features" className="hover:text-gray-900">Features</a>
                <a href="#download" className="hover:text-gray-900">Download</a>
              </div>
            </div>
            <div>
              <div className="font-semibold text-gray-900 mb-3">Resources</div>
              <div className="flex flex-col gap-2 text-gray-500">
                <a href={docs} target="_blank" rel="noreferrer" className="hover:text-gray-900">Docs</a>
                <a href={gh} target="_blank" rel="noreferrer" className="hover:text-gray-900">GitHub</a>
              </div>
            </div>
            <div>
              <div className="font-semibold text-gray-900 mb-3">Connect</div>
              <div className="flex flex-col gap-2 text-gray-500">
                <a href={gh} target="_blank" rel="noreferrer" className="hover:text-gray-900">GitHub</a>
              </div>
            </div>
          </div>
        </div>
        <div className="mt-10 pt-6 border-t border-gray-200 text-[12px] text-gray-400">\u00A9 2026 Nova. Built for everyday use.</div>
      </div>
    </footer>
  )
}
