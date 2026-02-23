import React, { useEffect, useMemo, useRef, useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { getScenarios, Scenario, startRun, streamLogs, getTest ,startRunMany,streamLogsUntilFinished} from '../lib/api'
import Console from '../components/Console'

type Row = Scenario & { selected?: boolean }

function sanitizeName(s: string) {
  return s.replace(/[^a-zA-Z0-9._-]+/g, '_')
}

function scenarioToDescription(sc: Scenario): string {
  const stepsArr = Array.isArray(sc.steps) ? sc.steps : (sc.steps ? [sc.steps] : [])
  const steps = stepsArr.map((s, i) => `${i + 1}. ${s}`).join('\n')
  return [
    sc.title || '',
    sc.preconditions ? `Preconditions: ${sc.preconditions}` : '',
    steps ? `Steps:\n${steps}` : '',
    sc.expected_results ? `Expected: ${sc.expected_results}` : ''
  ].filter(Boolean).join('\n\n')
}

export default function ScenarioSelect() {
  const { name = '' } = useParams()
  const [sp] = useSearchParams()
  const application_url = sp.get('url') || ''
  const fallbackDesc = sp.get('desc') || ''
  const [rows, setRows] = useState<Row[]>([])
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState<string | null>(null)

  // Runner state
  const [running, setRunning] = useState(false)
  const [current, setCurrent] = useState<{ id: string; runId: string } | null>(null)
  const [logs, setLogs] = useState<{ line?: string; status?: string }[]>([])
  const [results, setResults] = useState<{ scenarioId: string; testName: string; reportUrl?: string }[]>([])
  const stopRef = useRef<null | (() => void)>(null)

  useEffect(() => {
    (async () => {
      setLoading(true); setErr(null)
      try {
        const data = await getScenarios(name, application_url, fallbackDesc)
        setRows(data.map(d => ({ ...d, selected: true })))
      } catch (e:any) {
        setErr(e?.message || String(e))
      } finally {
        setLoading(false)
      }
    })()
  }, [name, application_url, fallbackDesc])

  const allChecked = useMemo(() => rows.length > 0 && rows.every(r => r.selected), [rows])
  const anyChecked = useMemo(() => rows.some(r => r.selected), [rows])

  const toggleAll = (checked: boolean) => setRows(prev => prev.map(r => ({ ...r, selected: checked })))
  const toggleOne = (id: string, checked: boolean) => setRows(prev => prev.map(r => r.id === id ? ({ ...r, selected: checked }) : r))

  async function runSequentially() {
    setRunning(true);
    setResults([]);
    setLogs([]);
    setCurrent(null);

    const selected = rows.filter(r => r.selected);
    if (selected.length === 0) return;

    // One run, one file: tests/{name}.spec.ts
    const { run_id } = await startRunMany({
      application_url,
      test_name: name,                 // <— base name; one file
      test_description: fallbackDesc || `${name} scenarios`,
      scenarios: selected,
    });

    setCurrent({ id: `${selected.length} scenario(s)`, runId: run_id });
    await streamLogsUntilFinished(run_id, (msg) => setLogs(prev => [...prev, msg]));

    // Fetch single combined report
    try {
      const t = await getTest(name);
      setResults([{ scenarioId: 'all', testName: name, reportUrl: t?.report_url }]);
    } catch {
      setResults([{ scenarioId: 'all', testName: name }]);
    }

    setCurrent(null);
    setRunning(false);
  }

  useEffect(() => () => { if (stopRef.current) stopRef.current() }, [])

  if (loading) return <div className="text-white/80">Loading scenarios…</div>
  if (err) return <div className="text-red-300">Error: {err}</div>
  if (!rows.length) return <div className="text-white/80">No scenarios were generated for this test.</div>

  return (
    <div className="space-y-6">
      <div className="glass neo rounded-2xl p-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-medium text-white">Select scenarios for <span className="font-mono">{name}</span></h2>
          <div className="flex items-center gap-3">
            <label className="text-white/80 text-sm flex items-center gap-2">
              <input
                type="checkbox"
                checked={allChecked}
                onChange={(e) => toggleAll(e.target.checked)}
              />
              Select all
            </label>
            <button
              onClick={runSequentially}
              disabled={!anyChecked || running || !application_url}
              className="btn-neo rounded-xl px-3 py-1.5 bg-brand-600 text-white disabled:opacity-50"
            >
              {running ? 'Running…' : `Generate & Run (${rows.filter(r => r.selected).length})`}
            </button>
          </div>
        </div>

        <div className="overflow-auto rounded-xl border border-white/10">
          <table className="min-w-full text-sm text-white/90">
            <thead className="bg-white/5 text-white/90">
              <tr>
                <th className="p-2 w-10"></th>
                <th className="p-2 text-left">ID</th>
                <th className="p-2 text-left">Title</th>
                <th className="p-2">Kind</th>
                <th className="p-2">Priority</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <React.Fragment key={r.id}>
                  <tr className="border-t border-white/10">
                    <td className="p-2 text-center">
                      <input
                        type="checkbox"
                        checked={!!r.selected}
                        onChange={(e) => toggleOne(r.id, e.target.checked)}
                      />
                    </td>
                    <td className="p-2 font-mono">{r.id}</td>
                    <td className="p-2">{r.title}</td>
                    <td className="p-2 text-center">{r.kind || '-'}</td>
                    <td className="p-2 text-center">{r.priority || '-'}</td>
                  </tr>
                  <tr className="border-t border-white/10 bg-white/5">
                    <td></td>
                    <td colSpan={4} className="p-3 text-white/70">
                      {r.preconditions && <div className="mb-2"><b>Preconditions:</b> {r.preconditions}</div>}
                      {Array.isArray(r.steps) ? (
                        <div className="mb-2">
                          <b>Steps:</b>
                          <ol className="list-decimal pl-6">
                            {r.steps.map((s, i) => <li key={i}>{s}</li>)}
                          </ol>
                        </div>
                      ) : r.steps ? <div className="mb-2"><b>Steps:</b> {r.steps}</div> : null}
                      {r.expected_results && <div><b>Expected:</b> {r.expected_results}</div>}
                    </td>
                  </tr>
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Live logs for the currently running scenario */}
      {running && (
        <div>
          <div className="mb-2 text-white/80">
            Running scenario: <span className="font-mono">{current?.id || '-'}</span>
          </div>
          <Console logs={logs} />
        </div>
      )}

      {/* Completed runs + report links */}
      {results.length > 0 && (
        <div className="glass neo rounded-2xl p-4">
          <h3 className="text-white text-lg mb-2">Finished</h3>
          <ul className="list-disc pl-6 text-white/90">
            {results.map((r) => (
              <li key={r.testName}>
                <span className="font-mono">{r.testName}</span>
                {r.reportUrl ? <> — <a className="text-brand-400 hover:underline" href={r.reportUrl} target="_blank">Report</a></> : null}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
