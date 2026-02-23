import React, { useEffect, useState, useRef } from 'react'
import { getTest, saveTestCode } from '../lib/api'
import { useParams } from 'react-router-dom'
import Report from '../components/Report'
import RunTestButton from "../components/RunTestButton"
import { startCodegen } from '../lib/api'

export default function TestDetail() {
  const { name } = useParams()
  const [code, setCode] = useState('')
  const [report, setReport] = useState('')
  const [meta, setMeta] = useState<any>(null)
  const [isEditing, setIsEditing] = useState(false)
  const [edited, setEdited] = useState('')
  const [saving, setSaving] = useState(false)
  const [launching, setLaunching] = useState(false)
  const editAreaRef = useRef<HTMLTextAreaElement | null>(null)


  useEffect(() => {
    if (!name) return
    getTest(name).then((res) => {
      setMeta(res.meta)
      setCode(res.code || '')
      setEdited(res.code || '')        
      setReport(res.report_text || '')
    }).catch(console.error)
  }, [name])

  return (
    <>
      <div className="glass neo rounded-2xl p-6">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-medium text-white">Test: {name}</h2>
          {meta?.last_status && (
            <span className={`px-2 py-0.5 rounded-lg text-xs ${
              meta.last_status === 'passed'
                ? 'bg-emerald-600/30 text-emerald-200'
                : 'bg-rose-600/30 text-rose-200'
            }`}>
              {meta.last_status}
            </span>
          )}
        </div>

        <div className="flex items-center justify-between mb-2">
          <h3 className="text-white/80 font-medium">Code</h3>
          {!isEditing ? (
            <div className="flex items-center gap-2">
              <button
                onClick={() => setIsEditing(true)}
                className="px-3 py-1.5 text-xs rounded-xl border border-white/10 hover:bg-white/10"
              >
                Edit
              </button>

              <button
                disabled={launching}
                onClick={async () => {
                  if (!name) return
                  try {
                    setLaunching(true)
                    await startCodegen(name, meta?.last_app_url)
                    window.alert(
                      'Playwright CodeGen launched.\n' +
                      'Record your steps.\n' +'Then In the Inspector, Stop the recording and close the recorder.\n' +
                      'Back here, click Refresh to load the generated code'
                    )
                  } finally {
                    setLaunching(false)
                  }
                }}
                className="px-3 py-1.5 text-xs rounded-xl border border-white/10 hover:bg-white/10 disabled:opacity-60"
                title="Open Playwright’s recorder; copy recorded code from Inspector and paste here"
              >
                {launching ? 'Launching…' : 'Fix with CodeGen'}
              </button>
              <button
                onClick={async () => {
                  if (!name) return
                  const res = await getTest(name)
                  setMeta(res.meta)
                  setCode(res.code || '')
                  setEdited(res.code || '')
                  setReport(res.report_text || '')
                }}
                className="px-3 py-1.5 text-xs rounded-xl border border-white/10 hover:bg-white/10"
                title="Reload the test file from disk"
              >
                Refresh
              </button>
            </div>
          
          ) : (
            <div className="flex gap-2">
              <button
                onClick={async () => {
                  if (!name) return
                  try {
                    setSaving(true)
                    await saveTestCode(name, edited)   // <--- make sure this matches exactly
                    setCode(edited)
                    setIsEditing(false)
                  } finally {
                    setSaving(false)
                  }
                }}
                disabled={saving}
                className="px-3 py-1.5 text-xs rounded-xl border border-emerald-600/40 bg-emerald-600/20 hover:bg-emerald-600/30 disabled:opacity-60"
              >
                {saving ? 'Saving…' : 'Save'}
              </button>
              <button onClick={() => { setEdited(code); setIsEditing(false); }}
                className="px-3 py-1.5 text-xs rounded-xl border border-white/10 hover:bg-white/10">
                Cancel
              </button>
            </div>
          )}
        </div>

        {!isEditing ? (
          <pre className="rounded-xl border border-white/10 bg-neutral-950 p-4 text-xs text-white/90 overflow-auto neo-inset">
{code || '// no code found'}
          </pre>
        ) : (
          <textarea
            ref={editAreaRef}
            className="w-full h-[360px] rounded-xl border border-white/10 bg-neutral-950 p-4 text-xs text-white/90 font-mono outline-none focus:ring-2 ring-emerald-500"
            value={edited}
            onChange={(e) => setEdited(e.target.value)}
          />
        )}
      </div>

      <div className="glass neo rounded-2xl p-6 mt-6">
        <h3 className="text-white/80 font-medium mb-2">Run this test</h3>
        {name && (
          <RunTestButton
            specSlug={name}
            onDone={() =>
              getTest(name!).then((res) => {
                setMeta(res.meta)
                setCode(res.code || '')
                setEdited(res.code || '')
                setReport(res.report_text || '')
                window.dispatchEvent(new Event('tests:updated')) 
              }).catch(console.error)
            }
          />
        )}
      </div>

      <Report md={report} />
    </>
  )
}
