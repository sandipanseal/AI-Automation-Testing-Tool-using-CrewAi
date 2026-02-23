from crewai.tools import BaseTool
import os
import subprocess
from pathlib import Path
from shutil import which

class CustomPlaywrightTool(BaseTool):
    name: str = "CustomPlaywrightTool"
    description: str = (
        "Runs a Playwright .spec.ts file by name (e.g., tests/login.spec.ts) and returns result."
    )

    def _find_playwright_cmd(self):
        local = Path("node_modules") / ".bin" / ("playwright.cmd" if os.name == "nt" else "playwright")
        if local.exists():
            return [str(local)]
        npx = which("npx")
        if npx:
            return [npx, "playwright"]
        return None

    def _run(self, filename: str, **kwargs):
        p = Path(filename)
        if not p.exists():
            alt = Path("tests") / filename
            if alt.exists():
                p = alt
        if not p.exists():
            return {"status": "fail", "stdout": "", "stderr": f"Spec not found: {filename}", "returncode": 2}

        cmd_base = self._find_playwright_cmd()
        if cmd_base is None:
            return {
                "status": "fail",
                "stdout": "",
                "stderr": "Playwright CLI not found. Run 'npm install' and 'npx playwright install'.",
                "returncode": 127,
            }

        cmd = cmd_base + ["test", str(p)]
        if os.environ.get("PLAYWRIGHT_HEADED", "").lower() in ("1", "true", "yes"):
            cmd.append("--headed")

        result = subprocess.run(cmd, capture_output=True, text=True)
        return {
            "status": "pass" if result.returncode == 0 else "fail",
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }

class StripTripleBackticksTool(BaseTool):
    name: str = "StripTripleBackticksTool"
    description: str = "Removes triple backticks and removes non-code text for specific file types."

    def _run(self, filename: str, **kwargs):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                content = f.read()
            cleaned = content.strip()
            # Remove triple backticks from the start
            if cleaned.startswith("```"):
                cleaned = cleaned[3:].lstrip('\n')
            # Remove triple backticks from the end
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3].rstrip('\n')
            # Remove any remaining triple backticks anywhere
            cleaned = cleaned.replace("```", "")

            lines = cleaned.splitlines()

            # Content-based cleaning for Playwright test files
            import_line = "import { test, expect } from '@playwright/test';"
            if any(import_line in line for line in lines):
                for idx, line in enumerate(lines):
                    if import_line in line:
                        lines = lines[idx:]
                        break
            # Content-based cleaning for JSON files
            elif any(line.lstrip().startswith(('[', '{')) for line in lines):
                while lines and not lines[0].lstrip().startswith(("[", "{")):
                    lines.pop(0)

            # Remove all lines after the last closing bracket (for code files)
            brackets = ('}', ']', ')')
            last_bracket_idx = None
            for idx in range(len(lines) - 1, -1, -1):
                if lines[idx].strip().endswith(brackets):
                    last_bracket_idx = idx
                    break
            if last_bracket_idx is not None:
                lines = lines[:last_bracket_idx + 1]

            cleaned = "\n".join(lines)

            with open(filename, "w", encoding="utf-8") as f:
                f.write(cleaned)
            return {"status": "success", "message": f"Backticks and extra text removed from {filename}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
