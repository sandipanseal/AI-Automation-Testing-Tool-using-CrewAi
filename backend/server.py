import asyncio
import os
import time
import json
from typing import Dict, AsyncGenerator, Optional,List, Any
import re
import glob
import sys, pathlib
import re
import platform
import sys, importlib.util 

from shutil import which
from fastapi import FastAPI, HTTPException, Path,Body
from fastapi.responses import PlainTextResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from shutil import which
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
from fastapi import APIRouter, HTTPException



try:
    from test_agent.crew import TestAutomationCrew  
except Exception:
    TestAutomationCrew = None  


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]  
OUTPUT_DIR = REPO_ROOT / 'output'
TESTS_DIR = REPO_ROOT / 'tests'
DATA_DIR = REPO_ROOT / 'data'
REPORTS_DIR = OUTPUT_DIR / 'reports'

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
SCENARIO_DIR = os.path.join(OUTPUT_DIR, 'Testcases')
INDEX_PATH = os.path.join(DATA_DIR, 'tests_index.json')
router = APIRouter()
os.makedirs(SCENARIO_DIR, exist_ok=True)

app = FastAPI()
app.include_router(router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


RUNS: Dict[str, Dict] = {}  

def sanitize_name(name: str) -> str:
    # keep test name filesystem-safe
    return re.sub(r'[^a-zA-Z0-9._-]+', '_', name).strip()

def _local_playwright_bin(repo_root: pathlib.Path) -> str | None:
    # prefer the repo-local playwright CLI over global npx
    bin_name = "playwright.cmd" if os.name == "nt" else "playwright"
    cand = repo_root / "node_modules" / ".bin" / bin_name
    return str(cand) if cand.exists() else None

def _has_display() -> bool:
    # Windows/macOS OK; on Linux we require DISPLAY for a GUI session
    if sys.platform.startswith("win") or sys.platform == "darwin":
        return True
    return bool(os.environ.get("DISPLAY"))

def _xvfb_available() -> bool:
    return which("xvfb-run") is not None

def _now_iso() -> str:
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

def _read_index() -> Dict[str, Dict]:
    if not os.path.exists(INDEX_PATH):
        return {}
    try:
        with open(str(INDEX_PATH), 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def _write_index(idx: Dict) -> None:
    with open(str(INDEX_PATH), 'w', encoding='utf-8') as f:
        json.dump(idx, f, indent=2)

def _ensure_test_in_index(test_name: str) -> None:
    idx = _read_index()
    if test_name not in idx:
        created = _now_iso()
        ts_path = os.path.join(TESTS_DIR, f'{test_name}.spec.ts')
        if os.path.exists(ts_path):
            created = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(os.path.getmtime(ts_path)))
        idx[test_name] = {
            'name': test_name,
            'created_at': created,
            'last_run_at': None,
            'last_status': None,
            'last_report_file': None,
            'last_app_url': None     
        }
        _write_index(idx)

def _update_test_after_run(test_name: str, status: Optional[str], report_rel: Optional[str]) -> None:
    idx = _read_index()
    _ensure_test_in_index(test_name)
    idx = _read_index()
    entry = idx[test_name]
    entry['last_run_at'] = _now_iso()
    if status:
        entry['last_status'] = status
    if report_rel:
        entry['last_report_file'] = report_rel
    _write_index(idx)

def _derive_status_from_report_text(text: str) -> Optional[str]:
    t = text.lower()
    if "'script pass/fail result': pass" in t or "script pass/fail result: pass" in t:
        return 'passed'
    if "'script pass/fail result': fail" in t or "script pass/fail result: fail" in t:
        return 'failed'
    if " pass" in t and " fail" not in t:
        return 'passed'
    if " fail" in t and " pass" not in t:
        return 'failed'
    return None

def _find_playwright_cmd():
    local = REPO_ROOT / "node_modules" / ".bin" / ("playwright.cmd" if os.name == "nt" else "playwright")
    if local.exists():
        return [str(local)]
    npx = which("npx")
    if npx:
        return [npx, "playwright"]
    raise RuntimeError("Playwright CLI not found. Run 'npm install' and 'npx playwright install'.")

def _status_from_last_run_json() -> Optional[str]:
    candidates = [
        os.path.join(REPO_ROOT, 'test-results', 'last-run.json'),
        os.path.join(REPO_ROOT, 'test-results', '.last-run.json'),
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # commonly { "status": "passed" | "failed" }
                s = (data.get('status') or '').lower().strip()
                if s in ('passed', 'failed'):
                    return s
            except Exception:
                continue
    return None

async def _enqueue_stream(proc: asyncio.subprocess.Process, q: asyncio.Queue, run_id: str) -> None:
    async def reader(stream):
        while True:
            line = await stream.readline()
            if not line:
                break
            await q.put({'line': line.decode(errors='ignore').rstrip()})

    try:
        await asyncio.gather(reader(proc.stdout), reader(proc.stderr))
    finally:
        await proc.wait()
        test_name = RUNS.get(run_id, {}).get('test_name', 'unknown')
        report_src = os.path.join(OUTPUT_DIR, 'final_report.md')
        report_rel = None
        status = _status_from_last_run_json()
        if os.path.exists(report_src):
            ts = int(time.time())
            safe_name = re.sub(r'[^a-zA-Z0-9._-]+', '_', test_name) if test_name else 'unknown'
            report_rel = f'reports/{safe_name}-{ts}.md'
            report_dst = os.path.join(OUTPUT_DIR, report_rel)
            try:
                import shutil
                shutil.copyfile(report_src, report_dst)
                if status is None:
                    with open(report_src, 'r', encoding='utf-8', errors='ignore') as f:
                        status = _derive_status_from_report_text(f.read())
            except Exception:
                pass
        _update_test_after_run(test_name, status, report_rel)
        await q.put({'status': 'finished'})


def _normalize_spec(spec: str) -> str:
    """
    Accepts 'tests\\foo.spec.ts', 'tests/foo.spec.ts', 'foo', 'tests\\foo'
    Returns forward-slash path relative to repo root.
    """
    s = spec.replace("\\", "/")
    p = (REPO_ROOT / s).resolve()
    if p.exists():
        return str(p.relative_to(REPO_ROOT)).replace("\\", "/")

    # Try with tests/ prefix
    if not s.startswith("tests/"):
        p2 = REPO_ROOT / "tests" / s
        if p2.exists():
            return str(p2.relative_to(REPO_ROOT)).replace("\\", "/")

    # Try common extensions
    base = s.removesuffix(".spec.ts").removesuffix(".test.ts").removesuffix(".ts")
    for ext in (".spec.ts", ".test.ts", ".ts"):
        cand = REPO_ROOT / "tests" / (base + ext)
        if cand.exists():
            return str(cand.relative_to(REPO_ROOT)).replace("\\", "/")

    # As a last resort, search by filename under tests/
    needle = pathlib.Path(base).name
    tests_dir = REPO_ROOT / "tests"
    if tests_dir.exists():
        for cand in tests_dir.rglob("*"):
            if cand.is_file() and cand.name.startswith(needle):
                return str(cand.relative_to(REPO_ROOT)).replace("\\", "/")

    # Return original (Playwright will error clearly)
    return s

class RunTestRequest(BaseModel):
    spec: str = Field(..., description="e.g. tests\\login.spec.ts or login")
    headed: bool = False


class CodegenRequest(BaseModel):
    device: Optional[str] = None
    url: Optional[str] = None       


def _extract_url_from_spec(spec_path: pathlib.Path) -> Optional[str]:
    """Best-effort: find a http(s) URL, preferring page.goto('...')."""
    try:
        txt = spec_path.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        return None

    m = re.search(r'\bgoto\s*\(\s*[\'"](https?://[^\'"\)]+)', txt)
    if m:
        return m.group(1).strip()

    m = re.search(r'[\'"](https?://[^\'"]+)[\'"]', txt)
    if m:
        return m.group(1).strip()
    return None

def _to_playwright_test_if_raw(code: str) -> str:
    # If already a test file, return as-is.
    if "from '@playwright/test'" in code or 'from "@playwright/test"' in code:
        return code

    # Raw codegen usually uses require('playwright') + IIFE
    if "require('playwright')" in code or 'require("playwright")' in code:
        # 1) unwrap IIFE body if present
        m = re.search(r'\(async\s*\(\)\s*=>\s*\{\s*([\s\S]*?)\s*\}\)\(\);\s*$', code)
        body = m.group(1) if m else code

        # 2) drop manual browser/context creation & closing
        body = re.sub(r'const\s+browser\s*=.*?;\s*', '', body, flags=re.S)
        body = re.sub(r'const\s+context\s*=.*?;\s*', '', body, flags=re.S)
        body = re.sub(r'const\s+page\s*=.*?;\s*', '', body, flags=re.S)
        body = re.sub(r'await\s+context\.close\(\);\s*', '', body)
        body = re.sub(r'await\s+browser\.close\(\);\s*', '', body)

        # 3) wrap into a proper Playwright Test
        return (
            "import { test, expect } from '@playwright/test';\n\n"
            "test('test', async ({ page }) => {\n"
            f"{body}\n"
            "});\n"
        )
    return code

def _scenarios_path(test_name: str) -> str:
    safe = sanitize_name(test_name).strip()
    return os.path.join(SCENARIO_DIR, f'{safe}_test_cases.json')

def _resolve_scenarios_path(test_name: str) -> Optional[str]:
    """Return an existing scenarios file path for a test name, if any."""
    expected = _scenarios_path(test_name)
    if os.path.isfile(expected):
        return expected

    safe = sanitize_name(test_name).strip()
    candidates = []

    if safe.endswith('_test'):
        base = safe[:-5]
        candidates.append(os.path.join(SCENARIO_DIR, f'{base}_test_cases.json'))

    candidates.extend(glob.glob(os.path.join(SCENARIO_DIR, f'*{safe}*test_cases.json')))

    for cand in candidates:
        if cand and os.path.isfile(cand):
            return cand
    return None

def _read_scenarios_file(path: str):
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        raw = f.read().strip()
    txt = raw
    # Clean stray 'json' prefix and/or code fences
    if txt.lower().startswith('json'):
        txt = txt.split('\n', 1)[1] if '\n' in txt else '[]'
    txt = txt.strip().strip('`')
    try:
        return json.loads(txt)
    except Exception:
        m = re.search(r'(\[.*\])', txt, flags=re.S)
        if not m:
            raise HTTPException(status_code=500, detail='Invalid scenarios JSON.')
        return json.loads(m.group(1))

async def _ensure_scenarios(test_name: str, app_url: str, test_desc: str):
    """Run crew in plan-only mode to generate scenarios if missing."""
    resolved = _resolve_scenarios_path(test_name)
    if resolved:
        return
    env = os.environ.copy()
    env.update({
        'APP_URL': app_url.strip(),
        'TEST_NAME': test_name.strip(),
        'TEST_DESC': test_desc.strip(),
        'FAST_PLAN_ONLY': '1',            # ← key
        'PYTHONUNBUFFERED': '1',
        'PYTHONIOENCODING': 'utf-8',
    })
    cmd = _crewai_cmd()  
    proc = await asyncio.create_subprocess_exec(
        *cmd, cwd=str(REPO_ROOT),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    stdout, stderr = await proc.communicate()
    resolved_after = _resolve_scenarios_path(test_name)
    if resolved_after:
        expected = _scenarios_path(test_name)
        if resolved_after != expected:
            try:
                import shutil
                shutil.copyfile(resolved_after, expected)
            except Exception:
                pass
        return

    out_tail = (stdout or b'').decode('utf-8', 'ignore')[-1200:]
    err_tail = (stderr or b'').decode('utf-8', 'ignore')[-1200:]
    detail = f"Scenario generation failed (exit {proc.returncode})."
    if err_tail.strip():
        detail += f" stderr: {err_tail.strip()}"
    elif out_tail.strip():
        detail += f" output: {out_tail.strip()}"
    raise HTTPException(status_code=500, detail=detail)

def _crewai_cmd():
    """
    Return the CLI to start a CrewAI run.
    Prefer the installed console script; fall back to module execution.
    """
    exe = which("crewai")
    if exe:
        return [exe, "run"]

    spec = importlib.util.find_spec("crewai.cli")
    if spec is not None:
        return [sys.executable, "-m", "crewai.cli", "run"]

    spec2 = importlib.util.find_spec("crewai")
    if spec2 is not None:
        return [sys.executable, "-m", "crewai", "run"]

    raise RuntimeError("CrewAI CLI not found. Install it in this venv (e.g. `pip install crewai`).")

# API Endpoints

@app.post('/api/run')
async def start_run(payload: Dict):
    """
    Start a new test run via `crewai run`. Expects:
    {
      "application_url": str,
      "test_name": str,
      "test_description": str
    }
    """
    required = ('application_url', 'test_name', 'test_description')
    if not all(k in payload and str(payload[k]).strip() for k in required):
        raise HTTPException(status_code=400, detail='Missing required fields.')

    run_id = str(int(time.time() * 1000))
    q: asyncio.Queue = asyncio.Queue()
    test_name = payload['test_name'].strip()
    RUNS[run_id] = {'q': q, 'test_name': test_name}

    _ensure_test_in_index(test_name)

    try:
        idx = _read_index()
        entry = idx.get(test_name, {}) or {}
        entry['last_app_url'] = payload['application_url'].strip()
        idx[test_name] = entry
        _write_index(idx)
    except Exception:
        pass

    # Environment for the crew
    env = os.environ.copy()
    env.update({
        'APP_URL': payload['application_url'].strip(),
        'TEST_NAME': test_name,
        'TEST_DESC': payload['test_description'].strip(),
        'PYTHONUNBUFFERED': '1',
        'PYTHONIOENCODING': 'utf-8'
    })

    # Launch crewai workflow
    cmd = _crewai_cmd()
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(REPO_ROOT),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )

    asyncio.create_task(_enqueue_stream(proc, q, run_id))
    return JSONResponse({'run_id': run_id})

@app.get('/api/stream/{run_id}')
async def stream(run_id: str):
    if run_id not in RUNS:
        raise HTTPException(status_code=404, detail='Invalid run id')
    q: asyncio.Queue = RUNS[run_id]['q']

    async def event_gen() -> AsyncGenerator[dict, None]:
        try:
            while True:
                msg = await q.get()
                yield {'event': 'message', 'data': json.dumps(msg)}
                if msg.get('status') == 'finished':
                    break
        finally:
            RUNS.pop(run_id, None)

    return EventSourceResponse(event_gen())

@app.get('/api/report')
async def get_report():
    path = os.path.join(OUTPUT_DIR, 'final_report.md')
    if not os.path.isfile(path):
        return PlainTextResponse('', status_code=404)
    return FileResponse(path, media_type='text/markdown')

@app.get('/api/artifacts')
async def list_artifacts():
    if not os.path.isdir(OUTPUT_DIR):
        return JSONResponse([])
    files = [f for f in os.listdir(OUTPUT_DIR) if os.path.isfile(os.path.join(OUTPUT_DIR, f))]
    return JSONResponse(files)

@app.get('/outputs/{file_path:path}')
async def serve_outputs(file_path: str):
    path = os.path.join(OUTPUT_DIR, file_path)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail='Not found')
    return FileResponse(path)



@app.get('/api/tests')
async def list_tests():
    if os.path.isdir(TESTS_DIR):
        for f in os.listdir(TESTS_DIR):
            if f.endswith('.spec.ts'):
                _ensure_test_in_index(f[:-8])  
    idx = _read_index()
    return JSONResponse(list(idx.values()))

@app.get('/api/tests/{name}')
async def get_test(name: str = Path(...)):
    idx = _read_index()
    meta = idx.get(name)
    if not meta:
        _ensure_test_in_index(name)
        idx = _read_index()
        meta = idx.get(name)

    code = ''
    code_path = os.path.join(TESTS_DIR, f'{name}.spec.ts')
    if os.path.exists(code_path):
        try:
            with open(code_path, 'r', encoding='utf-8', errors='ignore') as f:
                code = f.read()
        except Exception:
            pass

    report_text = ''
    report_url = None
    if meta and meta.get('last_report_file'):
        rp = os.path.join(OUTPUT_DIR, meta['last_report_file'])
        if os.path.exists(rp):
            try:
                with open(rp, 'r', encoding='utf-8', errors='ignore') as f:
                    report_text = f.read()
                report_url = f"/outputs/{meta['last_report_file']}"
            except Exception:
                pass

    return JSONResponse({
        'meta': meta,
        'code': code,
        'report_text': report_text,
        'report_url': report_url
    })

@app.put('/api/tests/{name}')
async def update_test(name: str, payload: Dict):
    """
    Update the source code of a generated test: tests/{name}.spec.ts
    Body: { "code": "<typescript>" }
    """
    code = payload.get("code")
    if code is None:
        raise HTTPException(status_code=400, detail='Missing "code" in body.')

    # sanitize to avoid traversal
    safe = re.sub(r'[^a-zA-Z0-9._-]+', '_', name).strip()
    if not safe:
        raise HTTPException(status_code=400, detail='Invalid test name.')

    dest = os.path.join(TESTS_DIR, f'{safe}.spec.ts')
    os.makedirs(os.path.dirname(dest), exist_ok=True)

    try:
        with open(dest, 'w', encoding='utf-8') as f:
            f.write(code)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Failed to save code: {e}')

    _ensure_test_in_index(safe)  
    return JSONResponse({"ok": True, "name": safe, "path": str(os.path.relpath(dest, REPO_ROOT))})

@app.post("/api/run-test")
async def api_run_test(req: RunTestRequest):
    spec = _normalize_spec(req.spec)
    cmd = _find_playwright_cmd() + ["test", spec]
    if req.headed:
        cmd.append("--headed")

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(REPO_ROOT),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()

    status = "passed" if proc.returncode == 0 else "failed"

    test_name = None
    s = spec.replace("\\", "/")
    m = re.search(r"tests/(.+?)\.spec\.ts$", s)
    if m:
        test_name = m.group(1)
    else:
        base = os.path.basename(s)
        test_name = base[:-8] if base.endswith(".spec.ts") else base

    # Write a simple text report so the UI can show the latest run
    ts = time.strftime('%Y%m%d-%H%M%S', time.gmtime())
    safe_name = re.sub(r'[^a-zA-Z0-9._-]+', '_', test_name) if test_name else 'unknown'
    report_rel = f'reports/{safe_name}-playwright-{ts}.txt'
    report_dst = os.path.join(OUTPUT_DIR, report_rel)
    os.makedirs(os.path.dirname(report_dst), exist_ok=True)
    try:
        with open(report_dst, 'w', encoding='utf-8') as f:
            f.write("Command: " + " ".join(cmd) + "\n")
            f.write(f"Return code: {proc.returncode}\n")
            f.write(f"Status: {status}\n\n")
            f.write("===== STDOUT =====\n")
            f.write(out.decode(errors="replace"))
            f.write("\n\n===== STDERR =====\n")
            f.write(err.decode(errors="replace"))
    except Exception:
        report_rel = None  # don't block on reporting

    # Persist meta
    try:
        _update_test_after_run(test_name, status, report_rel)
    except Exception:
        pass

    return {
        "spec": spec,
        "headed": req.headed,
        "returncode": proc.returncode,
        "status": status,
        "stdout": out.decode(errors="replace"),
        "stderr": err.decode(errors="replace"),
        "ran": " ".join(cmd),
    }

@app.post("/api/tests/{name}/codegen")
async def launch_codegen(name: str, req: CodegenRequest):
    safe = sanitize_name(name)
    dest_path = (TESTS_DIR / f"{safe}.spec.ts").resolve()
    tmp_path  = dest_path.parent / f"{safe}.spec.codegen.ts"

    # 1) explicit url from request (if provided)
    url = (getattr(req, "url", None) or "").strip() or None

    # 2) fallback: previously stored app URL in tests_index.json
    if not url:
        try:
            idx = _read_index()
            entry = idx.get(safe) or {}
            last = (entry.get("last_app_url") or "").strip()
            if last:
                url = last
        except Exception:
            pass

    # 3) fallback: try to extract from the existing spec (page.goto('...'))
    if not url:
        url = _extract_url_from_spec(dest_path)
    env = os.environ.copy()

    # Prefer local Playwright binary; fallback to global npx playwright
    local_bin = _local_playwright_bin(REPO_ROOT)
    cli = [local_bin] if local_bin else ["npx", "playwright"]

    # Probe supported targets from --help (do not use 'ts'/'typescript')
    help_proc = await asyncio.create_subprocess_exec(
        *cli, "codegen", "--help",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=str(REPO_ROOT),
        env=env,
    )
    help_out = (await help_proc.communicate())[0].decode("utf-8", "ignore")
    preferred = ["playwright-test", "test", "javascript", "python", "python-async", "java", "csharp"]

    def _supports(tkn: str) -> bool:
        # match as a whole word in help output
        import re
        return re.search(rf'(?m)\b{re.escape(tkn)}\b', help_out) is not None

    target = next((t for t in preferred if _supports(t)), None)
    if target:
        print(f"[codegen] using target: {target}")
    else:
        print("[codegen] WARNING: could not detect a supported --target; defaulting to JS (no --target).")

    # Build the command
    target = target or "test"
    cmd = [*cli, "codegen", "--output", str(tmp_path)]
    if target:
        cmd += ["--target", target]
    if getattr(req, "device", None):
        cmd += ["--device", req.device]
    if url:
        cmd += [url]

    # If Linux without GUI, try xvfb-run
    if not _has_display() and sys.platform.startswith("linux"):
        if _xvfb_available():
            cmd = ["xvfb-run", "-a", "-s", "-screen 0 1920x1080x24", *cmd]
            print("[codegen] no DISPLAY; using xvfb-run")
        else:
            return JSONResponse(
                status_code=500,
                content={"error": "No DISPLAY found and xvfb-run not available. Run in a desktop session or install xvfb."},
            )

    print("[codegen] launching:", cmd)
    print("[codegen] writing to TMP:", tmp_path)

    # Launch and stream output (so errors are visible)
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(REPO_ROOT),
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )

    async def _stream():
        assert proc.stdout is not None
        async for line in proc.stdout:
            print("[codegen]", line.decode("utf-8", "ignore").rstrip())

    async def _finalize():
        await proc.wait()
        try:
            # accept common variants just in case
            candidates = [
                tmp_path,
                tmp_path.with_suffix(".ts"),
                tmp_path.with_suffix(".js"),
                *[p for p in tmp_path.parent.glob(f"{safe}.spec.codegen.*")],
            ]
            cand = max(
                (p for p in candidates if p.exists() and p.stat().st_size > 0),
                key=lambda p: p.stat().st_mtime,
                default=None
            )
            if cand:
                # read + normalize (convert raw script to @playwright/test spec if needed)
                code = cand.read_text(encoding="utf-8", errors="ignore")
                code = _to_playwright_test_if_raw(code)

                # backup existing, then write normalized code
                if dest_path.exists():
                    backup = dest_path.with_suffix(dest_path.suffix + f".bak.{int(time.time())}")
                    dest_path.replace(backup)
                dest_path.write_text(code, encoding="utf-8")

                # cleanup tmp candidates
                for p in set(candidates):
                    if p.exists() and p != dest_path:
                        try:
                            p.unlink()
                        except:
                            pass
                print(f"[codegen] saved: {dest_path}")
            else:
                print("[codegen] no output produced — keeping previous spec.")
        except Exception as e:
            print("[codegen] finalize error:", e)

    asyncio.create_task(_stream())
    asyncio.create_task(_finalize())
    return {"launched": True, "spec": str(dest_path), "url": url}



class SaveCodeBody(BaseModel):
    code: str

@router.post("/api/tests/{name}/code")
async def save_test_code(name: str, body: SaveCodeBody):
    safe = sanitize_name(name)
    dest_path = (TESTS_DIR / f"{safe}.spec.ts").resolve()
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    code = (body.code or "").rstrip() + "\n"
    try:
        if dest_path.exists():
            backup = dest_path.with_suffix(dest_path.suffix + f".bak.{int(time.time())}")
            dest_path.replace(backup)
        dest_path.write_text(code, encoding="utf-8")
        return {"ok": True, "path": str(dest_path)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save: {e}")



@app.get("/api/diagnostics/codegen")
async def diag_codegen():
    info = {
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "has_display": _has_display(),
        "xvfb_available": _xvfb_available(),
        "local_playwright_bin": _local_playwright_bin(REPO_ROOT),
        "env_DISPLAY": os.environ.get("DISPLAY"),
    }
    async def _run(*args):
        p = await asyncio.create_subprocess_exec(
            *args, cwd=str(REPO_ROOT),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
        )
        out = (await p.communicate())[0].decode("utf-8", "ignore")
        return {"rc": p.returncode, "out": out}
    cli = [_local_playwright_bin(REPO_ROOT)] if _local_playwright_bin(REPO_ROOT) else ["npx", "playwright"]
    info["playwright_version"] = await _run(*cli, "--version")
    info["codegen_help"] = await _run(*cli, "codegen", "--help")
    return info

class ScenarioReq(BaseModel):
    application_url: str
    test_description: str

@app.get('/api/tests/{name}/scenarios')
async def get_or_create_scenarios(
    name: str = Path(...),
    application_url: str = "",
    test_description: str = "",
):
    safe = sanitize_name(name).strip()
    path = _resolve_scenarios_path(safe) or _scenarios_path(safe)

    if not os.path.isfile(path):
        if not (application_url and test_description):
            raise HTTPException(status_code=404, detail='Scenarios not found for this test.')
        await _ensure_scenarios(safe, application_url, test_description)
        path = _resolve_scenarios_path(safe) or _scenarios_path(safe)

    scenarios = _read_scenarios_file(path)
    return JSONResponse(scenarios)

class ScenarioItem(BaseModel):
    id: str
    title: Optional[str] = ""
    steps: Optional[Any] = None           
    expected_results: Optional[Any] = None
    preconditions: Optional[Any] = None
    priority: Optional[str] = None
    kind: Optional[str] = None

@app.post("/api/tests/{name}/run-many")
async def run_many(
    name: str,
    payload: Dict[str, Any] = Body(...)
):
    required = ("application_url", "test_name", "test_description", "scenarios")
    if not all(k in payload for k in required):
        raise HTTPException(status_code=400, detail="Missing required fields.")

    base_name = sanitize_name(payload["test_name"]).strip() or sanitize_name(name)
    application_url = str(payload["application_url"]).strip()
    desc = str(payload.get("test_description", "")).strip()
    scenarios_raw = payload.get("scenarios") or []
    if not isinstance(scenarios_raw, list) or not scenarios_raw:
        raise HTTPException(status_code=400, detail="No scenarios provided.")

    # normalize scenarios
    scenarios: List[ScenarioItem] = []
    for s in scenarios_raw:
        try:
            scenarios.append(ScenarioItem.model_validate(s))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid scenario: {e}")

    # Persist the exact selected scenarios so the script generator can use them
    cases_path = TESTS_DIR.parent / "output" / "Testcases" / f"{base_name}_test_cases.json"
    cases_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cases_path, "w", encoding="utf-8") as f:
        import json as _json
        _json.dump([s.model_dump() for s in scenarios], f, indent=2, ensure_ascii=False)

    # Build a *combined* description telling the generator to produce one spec with multiple tests
    import json as _json
    combined_desc = _json.dumps(
        {
            "note": "MULTI_SCENARIO",
            "instruction": "Generate ONE Playwright spec file with multiple tests: one test per scenario, in the given order. Use test.describe('Feature'), test.beforeEach to goto APP_URL (or BASE_URL), and test.describe.configure({ mode: 'serial' }) so they run one-by-one.",
            "scenarios": [s.model_dump() for s in scenarios],
        },
        ensure_ascii=False,
    )

    # Prepare run like /api/run
    run_id = str(int(time.time() * 1000))
    q: asyncio.Queue = asyncio.Queue()
    RUNS[run_id] = {"q": q, "test_name": base_name}
    _ensure_test_in_index(base_name)

    # remember app url for this test
    try:
        idx = _read_index()
        entry = idx.get(base_name, {}) or {}
        entry["last_app_url"] = application_url
        idx[base_name] = entry
        _write_index(idx)
    except Exception:
        pass

    env = os.environ.copy()
    env.update(
        {
            "APP_URL": application_url,
            "TEST_NAME": base_name,           # single file name
            "TEST_DESC": combined_desc,       # multi-scenario JSON
            "PYTHONUNBUFFERED": "1",
            "PYTHONIOENCODING": "utf-8",
        }
    )

    cmd = _crewai_cmd()
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(REPO_ROOT),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )

    asyncio.create_task(_enqueue_stream(proc, q, run_id))
    return JSONResponse({"run_id": run_id})