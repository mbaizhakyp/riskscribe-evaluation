#!/usr/bin/env python3
"""
Generate Table 1 baseline infographics for supplemental cases.

Systems:
  - gpt_img_1_5  : gpt-image-1.5
  - gpt_img_2    : gpt-image-2
  - ci_sol       : gpt-5.6-sol + code_interpreter
  - ci_luna      : gpt-5.6-luna + code_interpreter

Shared inputs from results/table1/inputs/cases.json
(requirement + data_block + knowledge_block).

Fair-comparison controls:
  - identical inputs per case
  - portrait canvas (image API: 1024x1536; CI target 1200x1500)
  - attempt budget 3; first success wins
  - no cherry-picking aesthetics

Outputs under results/table1/generations/<case_id>/<system>/
"""

from __future__ import annotations

import base64
import json
import os
import random
import time
import traceback
from pathlib import Path

from openai import OpenAI

ROOT = Path(__file__).resolve().parent.parent
CASES_PATH = ROOT / "results" / "table1" / "inputs" / "cases.json"
OUT_ROOT = ROOT / "results" / "table1" / "generations"
API_KEYS_PATH = ROOT / "api_keys.txt"

ATTEMPT_BUDGET = 3
IMAGE_SIZE = "1024x1536"  # closest portrait size on image API
CI_CANVAS = "1200x1500 pixels (portrait), dpi=150"

SYSTEMS = {
    "gpt_img_1_5": {"kind": "image", "model": "gpt-image-1.5"},
    "gpt_img_2": {"kind": "image", "model": "gpt-image-2"},
    "ci_sol": {"kind": "code_interp", "model": "gpt-5.6-sol"},
    "ci_luna": {"kind": "code_interp", "model": "gpt-5.6-luna"},
}


def load_openai_key() -> str:
    env = os.environ.get("OPENAI_API_KEY")
    if env:
        return env.strip()
    text = API_KEYS_PATH.read_text()
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("sk-"):
            return s
    lines = [ln.strip() for ln in text.splitlines()]
    for i, ln in enumerate(lines):
        if ln.lower().rstrip(":") in {"gpt", "openai"} and i + 1 < len(lines):
            if lines[i + 1].startswith("sk-"):
                return lines[i + 1]
    raise RuntimeError("OpenAI API key not found")


def image_prompt(case: dict) -> str:
    return f"""Create ONE complete public-safety / public-risk infographic as a single portrait poster image.

USER REQUIREMENT:
{case['requirement']}

RETRIEVED DATA (authoritative — use these exact values; do not invent, alter precision, or omit units):
{case['data_block']}

RETRIEVED KNOWLEDGE (only permitted source for contextual text, guidance, location, sources):
{case['knowledge_block']}

Design rules:
- Compose a full infographic, not a bare chart: clear headline, key number(s), at least one chart that fits the data shape, short guidance if present in knowledge, and a source line.
- Use ONLY numbers from the retrieved data. Do not add statistics that are not listed.
- Any hazard/guidance text must come from the retrieved knowledge; do not invent facts.
- Portrait layout, professional public-agency style, readable text.
- Single image only.
"""


def ci_instructions() -> str:
    return f"""You are a data-visualization assistant. You must use the python tool to write and EXECUTE matplotlib code that renders ONE complete infographic-style figure as a single PNG file, then return that file.

Compose the figure from the provided inputs. It should read as a public-facing infographic, not a bare chart: include a clear headline, at least one chart of the provided data (choose a chart type that fits the data's shape), and any key numbers or contextual information from the inputs, laid out on one canvas.

Rules:
- Use ONLY the values in the provided data table. Do not invent numbers, change precision, or omit units.
- Any text you display about context/guidance must come from the provided knowledge; do not add facts that are not in the inputs.
- Canvas: {CI_CANVAS}. Save as a single PNG. Do not produce multiple figures.
"""


def ci_user_prompt(case: dict) -> str:
    return f"""USER REQUIREMENT:
{case['requirement']}

RETRIEVED DATA (authoritative - use these exact values):
{case['data_block']}

RETRIEVED KNOWLEDGE (the only permitted source for contextual text):
{case['knowledge_block']}

Write and execute the matplotlib code now and return the PNG file."""


def already_done(case_id: str, system: str) -> bool:
    rec = OUT_ROOT / case_id / system / "run_record.json"
    if not rec.exists():
        return False
    try:
        data = json.loads(rec.read_text())
        return bool(data.get("generated_ok")) and Path(data.get("output_file", "")).exists()
    except Exception:
        return False


def save_record(case_id: str, system: str, record: dict) -> None:
    d = OUT_ROOT / case_id / system
    d.mkdir(parents=True, exist_ok=True)
    (d / "run_record.json").write_text(json.dumps(record, indent=2) + "\n")


def generate_image(client: OpenAI, case: dict, system: str, model: str) -> dict:
    case_id = case["case_id"]
    out_dir = OUT_ROOT / case_id / system
    out_dir.mkdir(parents=True, exist_ok=True)
    prompt = image_prompt(case)
    (out_dir / "prompt.txt").write_text(prompt)

    record = {
        "case_id": case_id,
        "system": system,
        "model": model,
        "kind": "image",
        "attempts_used": 0,
        "generated_ok": 0,
        "output_file": None,
        "errors": [],
        "run_date": time.strftime("%Y-%m-%d"),
        "image_size": IMAGE_SIZE,
    }

    for attempt in range(1, ATTEMPT_BUDGET + 1):
        record["attempts_used"] = attempt
        try:
            print(f"    image attempt {attempt}/{ATTEMPT_BUDGET} model={model}", flush=True)
            resp = client.images.generate(
                model=model,
                prompt=prompt,
                size=IMAGE_SIZE,
                n=1,
            )
            item = resp.data[0]
            b64 = getattr(item, "b64_json", None)
            if not b64:
                raise RuntimeError("No b64_json in image response")
            png_path = out_dir / f"{case_id}_{system}.png"
            png_path.write_bytes(base64.b64decode(b64))
            revised = getattr(item, "revised_prompt", None)
            if revised:
                (out_dir / f"attempt{attempt}_revised_prompt.txt").write_text(str(revised))
            record["generated_ok"] = 1
            record["output_file"] = str(png_path)
            break
        except Exception as e:
            err = f"attempt {attempt}: {e}"
            record["errors"].append(err)
            print(f"    FAIL {err}", flush=True)
            time.sleep(min(2 ** attempt, 20))

    save_record(case_id, system, record)
    return record


def _extract_code_blocks(resp) -> list[str]:
    codes = []
    for item in getattr(resp, "output", []) or []:
        itype = getattr(item, "type", None) or (item.get("type") if isinstance(item, dict) else None)
        if itype == "code_interpreter_call":
            code = getattr(item, "code", None) if not isinstance(item, dict) else item.get("code")
            if code:
                codes.append(code)
    return codes


def _download_ci_png(client: OpenAI, resp, dest: Path) -> bool:
    """Find container file citations and download first PNG-like file."""
    output = getattr(resp, "output", []) or []
    citations = []

    for item in output:
        if isinstance(item, dict):
            itype = item.get("type")
            content = item.get("content") or []
        else:
            itype = getattr(item, "type", None)
            content = getattr(item, "content", None) or []

        if itype != "message":
            continue
        for part in content:
            if isinstance(part, dict):
                anns = part.get("annotations") or []
            else:
                anns = getattr(part, "annotations", None) or []
            for ann in anns:
                if isinstance(ann, dict):
                    atype = ann.get("type")
                    container_id = ann.get("container_id")
                    file_id = ann.get("file_id")
                    filename = ann.get("filename") or ann.get("file_name") or ""
                else:
                    atype = getattr(ann, "type", None)
                    container_id = getattr(ann, "container_id", None)
                    file_id = getattr(ann, "file_id", None)
                    filename = getattr(ann, "filename", None) or getattr(ann, "file_name", None) or ""
                if atype == "container_file_citation" and container_id and file_id:
                    citations.append((container_id, file_id, filename))

    # Prefer png filenames; else try all
    citations_sorted = sorted(
        citations,
        key=lambda x: (0 if str(x[2]).lower().endswith(".png") else 1, x[2] or ""),
    )

    def _fetch_bytes(container_id: str, file_id: str) -> bytes:
        # openai SDK: client.containers.files.content.retrieve(file_id, container_id=...)
        data = client.containers.files.content.retrieve(file_id, container_id=container_id)
        if hasattr(data, "read"):
            return data.read()
        if hasattr(data, "content"):
            return data.content
        return bytes(data)

    for container_id, file_id, filename in citations_sorted:
        try:
            raw = _fetch_bytes(container_id, file_id)
            if len(raw) < 100:
                continue
            dest.write_bytes(raw)
            print(f"    downloaded {filename or file_id} ({len(raw)} bytes)", flush=True)
            return True
        except Exception as e:
            print(f"    download fail {filename or file_id}: {e}", flush=True)
            continue

    # Fallback: list container files if API supports it
    container_ids = {c[0] for c in citations}
    for item in output:
        itype = getattr(item, "type", None) if not isinstance(item, dict) else item.get("type")
        if itype == "code_interpreter_call":
            cid = getattr(item, "container_id", None) if not isinstance(item, dict) else item.get("container_id")
            if cid:
                container_ids.add(cid)

    for container_id in container_ids:
        try:
            files = client.containers.files.list(container_id=container_id)
            file_list = getattr(files, "data", files) or []
            for f in file_list:
                fname = getattr(f, "path", None) or getattr(f, "filename", None) or getattr(f, "id", "")
                fid = getattr(f, "id", None)
                if not fid:
                    continue
                try:
                    raw = _fetch_bytes(container_id, fid)
                    if raw[:8].startswith(b"\x89PNG") or raw[:2] == b"\xff\xd8":
                        dest.write_bytes(raw)
                        print(f"    downloaded via list {fname} ({len(raw)} bytes)", flush=True)
                        return True
                except Exception:
                    continue
        except Exception as e:
            print(f"    list container files failed: {e}", flush=True)

    return False


def generate_code_interp(client: OpenAI, case: dict, system: str, model: str) -> dict:
    case_id = case["case_id"]
    out_dir = OUT_ROOT / case_id / system
    out_dir.mkdir(parents=True, exist_ok=True)
    prompt = ci_user_prompt(case)
    (out_dir / "prompt.txt").write_text(prompt)

    record = {
        "case_id": case_id,
        "system": system,
        "model": model,
        "kind": "code_interp",
        "attempts_used": 0,
        "generated_ok": 0,
        "output_file": None,
        "errors": [],
        "run_date": time.strftime("%Y-%m-%d"),
        "canvas": CI_CANVAS,
    }

    for attempt in range(1, ATTEMPT_BUDGET + 1):
        record["attempts_used"] = attempt
        try:
            print(f"    CI attempt {attempt}/{ATTEMPT_BUDGET} model={model}", flush=True)
            resp = client.responses.create(
                model=model,
                tools=[{
                    "type": "code_interpreter",
                    "container": {"type": "auto", "memory_limit": "4g"},
                }],
                tool_choice="required",
                instructions=ci_instructions(),
                input=prompt,
            )

            # Save raw response summary
            try:
                raw_path = out_dir / f"attempt{attempt}_response.json"
                if hasattr(resp, "model_dump"):
                    raw_path.write_text(json.dumps(resp.model_dump(), indent=2, default=str)[:500000])
                else:
                    raw_path.write_text(str(resp)[:500000])
            except Exception:
                pass

            codes = _extract_code_blocks(resp)
            (out_dir / f"attempt{attempt}_code.py").write_text(
                "\n\n# ---- next call ----\n\n".join(codes) or "# no code returned\n"
            )

            png_path = out_dir / f"{case_id}_{system}.png"
            ok = _download_ci_png(client, resp, png_path)
            if ok and png_path.exists() and png_path.stat().st_size > 100:
                record["generated_ok"] = 1
                record["output_file"] = str(png_path)
                break
            else:
                raise RuntimeError("No PNG recovered from code_interpreter response")
        except Exception as e:
            err = f"attempt {attempt}: {e}"
            record["errors"].append(err)
            print(f"    FAIL {err}", flush=True)
            traceback.print_exc()
            time.sleep(min(2 ** attempt, 20))

    save_record(case_id, system, record)
    return record


def main() -> int:
    key = load_openai_key()
    client = OpenAI(api_key=key)
    cases = json.loads(CASES_PATH.read_text())
    OUT_ROOT.mkdir(parents=True, exist_ok=True)

    # optional filters
    only_systems = os.environ.get("ONLY_SYSTEMS", "").strip()
    systems = SYSTEMS
    if only_systems:
        wanted = {s.strip() for s in only_systems.split(",") if s.strip()}
        systems = {k: v for k, v in SYSTEMS.items() if k in wanted}

    only_cases = os.environ.get("ONLY_CASES", "").strip()
    if only_cases:
        wanted_c = {s.strip() for s in only_cases.split(",") if s.strip()}
        cases = [c for c in cases if c["case_id"] in wanted_c]

    print(f"Cases: {[c['case_id'] for c in cases]}", flush=True)
    print(f"Systems: {list(systems.keys())}", flush=True)
    print(f"Attempt budget: {ATTEMPT_BUDGET}", flush=True)

    results = []
    for case in cases:
        case_id = case["case_id"]
        for system, cfg in systems.items():
            if already_done(case_id, system):
                print(f"[SKIP] {case_id}/{system} already generated", flush=True)
                rec = json.loads((OUT_ROOT / case_id / system / "run_record.json").read_text())
                results.append(rec)
                continue
            print(f"[GEN] {case_id}/{system} ({cfg['model']})", flush=True)
            if cfg["kind"] == "image":
                rec = generate_image(client, case, system, cfg["model"])
            else:
                rec = generate_code_interp(client, case, system, cfg["model"])
            results.append(rec)
            print(
                f"  -> ok={rec['generated_ok']} attempts={rec['attempts_used']} file={rec.get('output_file')}",
                flush=True,
            )
            time.sleep(1)

    # manifest
    manifest = {
        "n_jobs": len(results),
        "n_ok": sum(1 for r in results if r.get("generated_ok")),
        "attempt_budget": ATTEMPT_BUDGET,
        "image_size": IMAGE_SIZE,
        "ci_canvas": CI_CANVAS,
        "systems": {k: v["model"] for k, v in SYSTEMS.items()},
        "results": results,
    }
    (OUT_ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(
        f"\nDone: {manifest['n_ok']}/{manifest['n_jobs']} generations succeeded",
        flush=True,
    )
    print(f"Manifest: {OUT_ROOT / 'manifest.json'}", flush=True)
    return 0 if manifest["n_ok"] == manifest["n_jobs"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
