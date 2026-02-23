import React, { useEffect, useState } from 'react'
import { listTests } from '../lib/api'
import { useNavigate } from 'react-router-dom'

type Row = {
  name: string
  created_at: string | null
  last_run_at: string | null
  last_status: string | null
}

export default function Tests() {
  const [rows, setRows] = useState<Row[]>([])
  const navigate = useNavigate()

  const fetchAll = async () => {
    try {
      const data = await listTests()  
      setRows(data)
    } catch (e) {
      console.error(e)
    }
  }

  useEffect(() => {
    fetchAll()

    const reload = () => fetchAll()
    const onVis = () => { if (!document.hidden) fetchAll() }

    window.addEventListener('tests:updated', reload)
    window.addEventListener('focus', reload)
    document.addEventListener('visibilitychange', onVis)

    return () => {
      window.removeEventListener('tests:updated', reload)
      window.removeEventListener('focus', reload)
      document.removeEventListener('visibilitychange', onVis)
    }
  }, [])

  return (
    <div className="glass neo rounded-2xl p-4">
      <h2 className="text-lg font-medium text-white mb-3">All Tests</h2>
      <div className="overflow-auto">
        <table className="min-w-full text-sm">
          <thead className="text-white/70">
            <tr>
              <th className="text-left p-2">Test Name</th>
              <th className="text-left p-2">Created</th>
              <th className="text-left p-2">Last Run</th>
              <th className="text-left p-2">Status</th>
            </tr>
          </thead>
          <tbody className="text-white/90">
            {rows.map((r) => (
              <tr key={r.name} className="hover:bg-white/5 cursor-pointer"
                  onClick={() => navigate(`/tests/${encodeURIComponent(r.name)}`)}>
                <td className="p-2">{r.name}</td>
                <td className="p-2">{r.created_at ?? '-'}</td>
                <td className="p-2">{r.last_run_at ?? '-'}</td>
                <td className="p-2">
                  {r.last_status ? (
                    <span className={`px-2 py-0.5 rounded-lg text-xs ${
                      r.last_status === 'passed'
                        ? 'bg-emerald-600/30 text-emerald-200'
                        : 'bg-rose-600/30 text-rose-200'
                    }`}>
                      {r.last_status}
                    </span>
                  ) : '-'}
                </td>
              </tr>
            ))}
            {!rows.length && (
              <tr><td className="p-2 text-white/60" colSpan={4}>No tests yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
