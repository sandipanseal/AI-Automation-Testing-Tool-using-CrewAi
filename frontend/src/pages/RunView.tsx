import React, { useEffect, useState } from 'react'
import Console from '../components/Console'
import Report from '../components/Report'
import { streamLogs, fetchReport, listArtifacts } from '../lib/api'
import { useParams } from 'react-router-dom'

type LogMsg = { line?: string; status?: string }

export default function RunView() {
  const { runId } = useParams()
  const [logs, setLogs] = useState<LogMsg[]>([])
  const [report, setReport] = useState('')
  const [artifacts, setArtifacts] = useState<string[]>([])

  useEffect(() => {
    if (!runId) return
    const stop = streamLogs(runId, async (msg) => {
      setLogs((prev) => [...prev, msg])
      if (msg.status === 'finished') {
        const [md, arts] = await Promise.all([fetchReport(), listArtifacts()])
        setReport(md || '')
        setArtifacts(arts || [])
      }
    })
    return () => stop()
  }, [runId])

  return (
    <>
      <Console logs={logs} />
      <Report md={report} />
      {!!artifacts.length && (
        <div className="glass neo rounded-2xl p-6">
          <h2 className="text-lg font-medium text-white mb-2">Artifacts</h2>
          <ul className="list-disc pl-6 text-white/90">
            {artifacts.map((f) => (
              <li key={f}>
                <a className="text-brand-400 hover:underline" target="_blank" href={`/outputs/${encodeURIComponent(f)}`}>{f}</a>
              </li>
            ))}
          </ul>
        </div>
      )}
    </>
  )
}
