import React from 'react'

type Props = { md: string }
export default function Report({ md }: { md: string }) {
  if (!md) return null
  return (
    <div className="glass neo rounded-2xl p-6">
      <h2 className="text-lg font-medium text-white mb-3">Final Report</h2>
      <article className="prose prose-slate max-w-none dark:prose-invert">
        <pre className="text-sm whitespace-pre-wrap text-white/90">{md}</pre>
      </article>
    </div>
  )
}