import React, { useState } from 'react'

type Props = {
  onSubmit: (x: { application_url: string, test_name: string, test_description: string }) => void
  isRunning: boolean
}

export default function Form({ onSubmit, isRunning }: Props) {
  const [application_url, setUrl] = useState('')
  const [test_name, setName] = useState('')
  const [test_description, setDesc] = useState('')

  return (
    <div className="glass card-3d rounded-2xl p-6 shadow-neo">
      <h2 className="text-white text-lg font-medium mb-4">New Test</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <label className="text-sm text-white/80">Application URL
          <input
            className="mt-1 w-full rounded-xl bg-neutral-900 border border-white/10 px-3 py-2 text-white placeholder-white/30 focus:outline-none focus:ring-2 focus:ring-brand-500"
            placeholder="https://your-app.example.com"
            value={application_url} onChange={e=>setUrl(e.target.value)}
          />
        </label>
        <label className="text-sm text-white/80">Test Name
          <input
            className="mt-1 w-full rounded-xl bg-neutral-900 border border-white/10 px-3 py-2 text-white placeholder-white/30 focus:outline-none focus:ring-2 focus:ring-brand-500"
            placeholder="Login flow smoke test"
            value={test_name} onChange={e=>setName(e.target.value)}
          />
        </label>
        <label className="md:col-span-2 text-sm text-white/80">Test Description
          <textarea
            className="mt-1 w-full rounded-xl bg-neutral-900 border border-white/10 px-3 py-2 text-white placeholder-white/30 focus:outline-none focus:ring-2 focus:ring-brand-500 min-h-[100px]"
            placeholder="Describe the scenario to generate & execute..."
            value={test_description} onChange={e=>setDesc(e.target.value)}
          />
        </label>
      </div>
      <div className="mt-4 flex gap-3">
        <button
          onClick={()=>onSubmit({ application_url,  test_name:test_name.trim(), test_description: test_description.trim() })}
          disabled={isRunning || !application_url || !test_name || !test_description}
          className="btn-neo rounded-xl px-4 py-2 bg-brand-600 text-white disabled:opacity-50 hover:bg-brand-500 transition"
        >
          {isRunning ? 'Running…' : 'Run Test'}
        </button>
        <p className="text-white/50 text-sm mt-2"></p>
      </div>
    </div>
  )
}