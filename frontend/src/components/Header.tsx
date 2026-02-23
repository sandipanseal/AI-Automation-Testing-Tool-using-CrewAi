import React from 'react'
export default function Header() {
  return (
    <header className="sticky top-0 z-20 backdrop-blur supports-[backdrop-filter]:bg-transparent">
      <div className="mx-auto max-w-6xl px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <img src="/artificial-intelligence.png" alt="Artificial Intelligence" className="w-8 h-8 rounded-xl neo-sm" />
          <div className="leading-tight">
            <div className="text-base font-semibold text-white">AI Testing Tool</div>
            <div className="text-xs text-neutral-600 dark:text-white/60">Powered by crewAI</div>
          </div>
        </div>
        <div className="text-xs text-neutral-600 dark:text-white/50">v0.1</div>
      </div>
    </header>
  )
}
