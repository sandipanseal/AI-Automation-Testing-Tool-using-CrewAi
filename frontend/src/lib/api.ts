export type RunPayload = {
  application_url: string;
  test_name: string;
  test_description: string;
}

export type RunResponse = { run_id: string };

export async function startRun(payload: RunPayload): Promise<RunResponse> {
  const res = await fetch('/api/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export function streamLogs(runId: string, onMessage: (data: any) => void) {
  const es = new EventSource(`/api/stream/${runId}`);
  es.onmessage = (e) => {
    try { onMessage(JSON.parse(e.data)); } catch { /* ignore */ }
  };
  return () => es.close();
}

export async function fetchReport(): Promise<string> {
  const res = await fetch('/api/report');
  if (res.status === 404) return '';
  if (!res.ok) throw new Error(await res.text());
  return res.text();
}

export async function listArtifacts(): Promise<string[]> {
  const res = await fetch('/api/artifacts');
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function listTests(): Promise<any[]> {
  const res = await fetch(`/api/tests?bust=${Date.now()}`, { cache: 'no-store' })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

/* export async function getTest(name: string): Promise<any> {
  const res = await fetch(`/api/tests/${encodeURIComponent(name)}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
} */

export async function saveTestCode(name: string, code: string): Promise<{ok: boolean}> {
  const res = await fetch(`/api/tests/${encodeURIComponent(name)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code })
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
} 

export async function startCodegen(name: string, url?: string) {
  const res = await fetch(`/api/tests/${encodeURIComponent(name)}/codegen`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(url ? { url } : {}),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}



export async function getTest(name: string) {
  const res = await fetch(`/api/tests/${encodeURIComponent(name)}`, {
    method: "GET",
    cache: "no-store",
    headers: { "Accept": "application/json" }
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export type Scenario = {
  id: string;
  title: string;
  preconditions?: string;
  steps: string[] | string;
  expected_results?: string;
  priority?: string;
  kind?: string;
};

export async function getScenarios(
  name: string,
  url: string,
  desc: string
): Promise<Scenario[]> {
  const qs = new URLSearchParams({
    application_url: url,
    test_description: desc,
  });
  const res = await fetch(`/api/tests/${encodeURIComponent(name)}/scenarios?${qs.toString()}`, {
    headers: { "Accept": "application/json" },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(await res.text());
  const data = await res.json();
  if (!Array.isArray(data)) {
    throw new Error(`Expected array of scenarios, got ${typeof data}: ${JSON.stringify(data).slice(0, 100)}`);
  }
  return data;
}

export async function startRunMany(payload: {
  application_url: string;
  test_name: string;
  test_description: string;
  scenarios: Scenario[];
}): Promise<RunResponse> {
  const res = await fetch(`/api/tests/${encodeURIComponent(payload.test_name)}/run-many`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export function streamLogsUntilFinished(runId: string, onMessage: (data: any) => void) {
  return new Promise<void>((resolve) => {
    const es = new EventSource(`/api/stream/${runId}`);
    es.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        onMessage(msg);
        if (msg?.status === 'finished') {
          es.close();
          resolve();
        }
      } catch {

      }
    };
  });
}








