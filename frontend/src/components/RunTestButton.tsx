import { useState } from "react";

export default function RunTestButton({
  specSlug,
  onDone,
}: { specSlug: string, onDone?: (r: any) => void }) {
  const spec = `tests/${specSlug}.spec.ts`;

  const [headed, setHeaded] = useState(false);
  const [running, setRunning] = useState(false);
  const [out, setOut] = useState<string>("");

  const runNow = async () => {
    setRunning(true);
    setOut("Running…");
    try {
      const res = await fetch(`/api/run-test`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ spec, headed }),
      });
      const raw = await res.text();
      let data: any = {};
      try { data = raw ? JSON.parse(raw) : {}; } catch { data = { raw }; }
      if (!res.ok) {
        setOut(`HTTP ${res.status} ${res.statusText}\n${raw || "(no response body)"}`);
        return;
      }
      setOut(
        `Command: ${data.ran}\nStatus: ${data.status} (code ${data.returncode})\n\n${data.stdout}` +
        (data.stderr ? `\n--- stderr ---\n${data.stderr}` : "")
      );
      if (onDone) onDone(data);    
    } catch (e: any) {
      setOut(`Request failed: ${e?.message || e}`);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-3">
        <button
          onClick={runNow}
          disabled={running}
          className="px-4 py-2 rounded-2xl shadow border hover:opacity-90 disabled:opacity-60"
          title={`Re-run ${spec}`}
        >
          {running ? "Running…" : "Run"}
        </button>

        <label className="flex items-center gap-2 text-sm opacity-80">
          <input type="checkbox" checked={headed} onChange={(e) => setHeaded(e.target.checked)} />
          Run headed (opens browser)
        </label>

        <span className="text-sm opacity-60">Spec: {spec}</span>
      </div>

      <pre className="whitespace-pre-wrap text-sm rounded-2xl p-3 bg-black/40 max-h-[50vh] overflow-auto">
        {out}
      </pre>
    </div>
  );
}
