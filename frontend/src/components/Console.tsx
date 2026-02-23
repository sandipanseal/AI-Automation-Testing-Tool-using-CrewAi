import React, { useEffect, useRef } from 'react'

export default function Console({ logs }: { logs: { line?: string; status?: string }[] }) {
  const endRef = useRef<HTMLDivElement | null>(null)
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [logs])
  return (
    <div className="glass neo rounded-2xl p-4 font-mono text-xs text-white/80">
      <h2 className="text-white text-lg font-medium mb-3">Live Logs</h2>
      <div className="max-h-[50vh] overflow-auto">
        {logs.map((l, i) => (
          <div key={i} className={l.status === 'finished' ? 'text-emerald-300' : ''}>
            {l.line ?? (l.status ? `== ${l.status.toUpperCase()} ==` : '')}
          </div>
        ))}
        <div ref={endRef} />
      </div>
    </div>
  )
}

