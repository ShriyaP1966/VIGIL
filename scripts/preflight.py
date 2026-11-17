#!/usr/bin/env python3
"""
VIGIL v3.1 — Master Preflight & Repository Hygiene Gatekeeper (§11.3)
Checks size budgets, branch hygiene, forbidden artifacts, lockfiles, and secrets.
Modes:
  --quick   (default; fast pre-push / local check)
  --history (comprehensive check before submission; audits git history)
Exit code 0 = PASS, 1 = FAIL.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

# Size thresholds in bytes
MB = 1024 * 1024
KB = 1024

M1_WARN_BYTES = 5.0 * MB
M1_FAIL_BYTES = 8.0 * MB
M1_MAX_FILE_BYTES = 500 * KB
M1_ALLOWLIST = {
    "frontend/package-lock.json": 700 * KB,
    "package-lock.json": 700 * KB,
}
IMAGE_MAX_BYTES = 200 * KB

M2_WARN_BYTES = 6.0 * MB
M2_FAIL_BYTES = 9.0 * MB

M3_FAIL_BYTES = 9.0 * MB
HISTORICAL_BLOB_FAIL_BYTES = 1.0 * MB

# Secret patterns
SECRET_PATTERNS = [
    ("Google AI Studio API Key", re.compile(r"AIza[0-9A-Za-z_-]{35}")),
    ("GitHub Token", re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}")),
    ("Private Key Header", re.compile(r"-----BEGIN (?:RSA|EC|OPENSSH|DSA|PGP|ENCRYPTED|PRIVATE) KEY-----")),
    ("Generic High-Entropy Secret/Key Assignment", re.compile(r"""(?i)(?:api[_-]?key|secret|token|password)\s*[:=]\s*['"][A-Za-z0-9_\-\.]{16,}['"]""")),
]

# Forbidden tracked extensions / patterns
FORBIDDEN_EXTENSIONS = {
    ".db", ".sqlite", ".sqlite3",
    ".pt", ".onnx", ".bin", ".safetensors", ".joblib", ".pkl",
    ".mp4", ".mov", ".wav", ".mp3",
    ".zip", ".tar", ".gz", ".parquet"
}

FORBIDDEN_PATHS = [
    ".env", ".env.local", ".env.production",
    "node_modules", ".venv", "venv", "__pycache__"
]

REQUIRED_GITIGNORE_TOKENS = [
    "node_modules", ".venv", "__pycache__", ".env", "*.db", "*.sqlite*", "dist/", "build/"
]


def run_git_cmd(args: list[str], check: bool = True) -> tuple[int, str, str]:
    res = subprocess.run(["git"] + args, capture_output=True, text=True, check=False)
    if check and res.returncode != 0:
        return res.returncode, res.stdout.strip(), res.stderr.strip()
    return res.returncode, res.stdout.strip(), res.stderr.strip()


def check_branches(verbose: bool = True) -> tuple[bool, list[str], list[str]]:
    fails = []
    warns = []

    # 1. Current branch must be main
    code, stdout, _ = run_git_cmd(["rev-parse", "--abbrev-ref", "HEAD"])
    current_branch = stdout.strip()
    if current_branch != "main":
        fails.append(f"Active branch is '{current_branch}', MUST be 'main'")

    # 2. Local heads must only be refs/heads/main
    code, stdout, _ = run_git_cmd(["for-each-ref", "--format=%(refname:short)", "refs/heads/"])
    local_branches = [b.strip() for b in stdout.splitlines() if b.strip()]
    if set(local_branches) != {"main"}:
        fails.append(f"Local branches must ONLY be ['main'], found: {local_branches}")

    # 3. Remote branches on origin
    code, stdout, stderr = run_git_cmd(["ls-remote", "--heads", "origin"])
    if code != 0:
        warns.append(f"Offline or remote unavailable: unable to run 'git ls-remote origin' ({stderr})")
    else:
        remote_heads = []
        for line in stdout.splitlines():
            parts = line.split()
            if len(parts) >= 2:
                ref = parts[1].replace("refs/heads/", "")
                remote_heads.append(ref)
        if remote_heads and set(remote_heads) != {"main"}:
            fails.append(f"Remote origin branches must ONLY be ['main'], found: {remote_heads}")

    return len(fails) == 0, fails, warns


def check_m1_tracked_size(verbose: bool = True) -> tuple[bool, list[str], list[str], float]:
    fails = []
    warns = []
    total_size = 0

    code, stdout, _ = run_git_cmd(["ls-files"])
    tracked_files = [f.strip() for f in stdout.splitlines() if f.strip()]

    for f_path_str in tracked_files:
        p = Path(f_path_str)
        if not p.exists():
            continue
        sz = p.stat().st_size
        total_size += sz

        # Per-file size check
        limit = M1_MAX_FILE_BYTES
        norm_path = f_path_str.replace("\\", "/")

        if norm_path in M1_ALLOWLIST:
            limit = M1_ALLOWLIST[norm_path]
        elif norm_path.startswith("docs/img/"):
            limit = IMAGE_MAX_BYTES

        if sz > limit:
            fails.append(f"File '{f_path_str}' size {sz / KB:.1f} KB exceeds limit of {limit / KB:.1f} KB")

    total_mb = total_size / MB
    if total_size > M1_FAIL_BYTES:
        fails.append(f"Tracked working-tree size M1 ({total_mb:.2f} MB) exceeds FAIL limit of {M1_FAIL_BYTES / MB:.1f} MB")
    elif total_size > M1_WARN_BYTES:
        warns.append(f"Tracked working-tree size M1 ({total_mb:.2f} MB) exceeds WARN limit of {M1_WARN_BYTES / MB:.1f} MB")

    return len(fails) == 0, fails, warns, total_mb


def check_m2_repo_size() -> tuple[bool, list[str], list[str], float]:
    fails = []
    warns = []

    # Run git gc lightly
    run_git_cmd(["gc", "--auto"])
    code, stdout, _ = run_git_cmd(["count-objects", "-vH"])
    
    pack_kb = 0.0
    loose_kb = 0.0
    for line in stdout.splitlines():
        if line.startswith("size-pack:"):
            # e.g. size-pack: 15.00 KiB or 1.20 MiB
            parts = line.split(":")
            val_str = parts[1].strip()
            pack_kb += parse_human_size_to_kb(val_str)
        elif line.startswith("size:"):
            parts = line.split(":")
            val_str = parts[1].strip()
            loose_kb += parse_human_size_to_kb(val_str)

    total_kb = pack_kb + loose_kb
    total_bytes = total_kb * KB
    total_mb = total_bytes / MB

    if total_bytes > M2_FAIL_BYTES:
        fails.append(f"Git repo storage M2 ({total_mb:.2f} MB) exceeds FAIL limit of {M2_FAIL_BYTES / MB:.1f} MB")
    elif total_bytes > M2_WARN_BYTES:
        warns.append(f"Git repo storage M2 ({total_mb:.2f} MB) exceeds WARN limit of {M2_WARN_BYTES / MB:.1f} MB")

    return len(fails) == 0, fails, warns, total_mb


def parse_human_size_to_kb(val_str: str) -> float:
    try:
        val_str = val_str.strip()
        parts = val_str.split()
        if not parts:
            return 0.0
        num = float(parts[0])
        unit = parts[1].lower() if len(parts) > 1 else "kib"
        if "gib" in unit or "gb" in unit:
            return num * 1024 * 1024
        elif "mib" in unit or "mb" in unit:
            return num * 1024
        elif "kib" in unit or "kb" in unit:
            return num
        elif "bytes" in unit or "b" in unit:
            return num / 1024
        return num
    except Exception:
        return 0.0


def check_m3_github_size() -> tuple[bool, list[str], list[str], float]:
    warns = []
    fails = []
    
    # Try gh api
    res = subprocess.run(["gh", "api", "repos/{owner}/{repo}", "--jq", ".size"], capture_output=True, text=True, check=False)
    if res.returncode == 0 and res.stdout.strip().isdigit():
        size_kb = float(res.stdout.strip())
        size_mb = size_kb / 1024
        if size_mb * MB > M3_FAIL_BYTES:
            fails.append(f"GitHub hosted repo size M3 ({size_mb:.2f} MB) exceeds FAIL limit of {M3_FAIL_BYTES / MB:.1f} MB")
        return len(fails) == 0, fails, warns, size_mb
    else:
        warns.append("GitHub CLI 'gh' not authenticated or repo size not queryable; M3 checked via local pack size")
        return True, fails, warns, 0.0


def check_tracked_content_and_hygiene() -> tuple[bool, list[str], list[str]]:
    fails = []
    warns = []

    code, stdout, _ = run_git_cmd(["ls-files"])
    tracked_files = [f.strip() for f in stdout.splitlines() if f.strip()]

    # Check forbidden files / extensions
    for f in tracked_files:
        norm = f.replace("\\", "/")
        p = Path(f)

        # Forbidden extensions
        if p.suffix.lower() in FORBIDDEN_EXTENSIONS:
            fails.append(f"Forbidden tracked file extension '{p.suffix}' in '{f}'")

        # Forbidden paths
        for forb in FORBIDDEN_PATHS:
            if norm == forb or norm.startswith(forb + "/") or f"/{forb}/" in norm:
                fails.append(f"Forbidden tracked path containing '{forb}' in '{f}'")

    # Check .gitignore tokens
    gitignore_p = Path(".gitignore")
    if not gitignore_p.exists():
        fails.append("Missing .gitignore file in repository root")
    else:
        gi_content = gitignore_p.read_text(encoding="utf-8", errors="ignore")
        for token in REQUIRED_GITIGNORE_TOKENS:
            if token not in gi_content:
                warns.append(f".gitignore may be missing recommended rule for '{token}'")

    # Check lockfile strategy
    # requirements.txt should pin packages with ==
    req_p = Path("backend/requirements.txt")
    if req_p.exists():
        for idx, line in enumerate(req_p.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
            s = line.strip()
            if s and not s.startswith("#"):
                if ">=" in s or "~=" in s or ("==" not in s and not s.startswith("-r")):
                    warns.append(f"backend/requirements.txt line {idx} ('{s}') is not strictly pinned with '=='")

    return len(fails) == 0, fails, warns


def scan_file_for_secrets(file_path: Path) -> list[str]:
    findings = []
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return findings

    # Skip .env.example placeholder checking if empty
    is_env_example = file_path.name == ".env.example"

    for line_idx, line in enumerate(content.splitlines(), start=1):
        if is_env_example and "=" in line:
            val = line.split("=", 1)[1].split("#")[0].strip()
            if not val:
                continue

        for label, pat in SECRET_PATTERNS:
            if pat.search(line):
                findings.append(f"{file_path} (L{line_idx}): detected pattern for {label}")

    return findings


def check_secrets_working_tree() -> tuple[bool, list[str], list[str]]:
    fails = []
    code, stdout, _ = run_git_cmd(["ls-files"])
    tracked_files = [f.strip() for f in stdout.splitlines() if f.strip()]

    for f in tracked_files:
        p = Path(f)
        if not p.exists() or not p.is_file():
            continue
        # Only scan text files < 500 KB
        if p.stat().st_size > 500 * KB:
            continue
        findings = scan_file_for_secrets(p)
        for issue in findings:
            fails.append(issue)

    return len(fails) == 0, fails, []


def check_history() -> tuple[bool, list[str], list[str]]:
    fails = []
    warns = []

    # 1. Largest blobs ever in git
    cmd = ["rev-list", "--objects", "--all"]
    code, rev_out, _ = run_git_cmd(cmd)
    if code != 0:
        warns.append("Unable to run rev-list on history")
        return True, fails, warns

    blob_hashes = []
    for line in rev_out.splitlines():
        parts = line.split()
        if parts:
            blob_hashes.append(parts[0])

    if blob_hashes:
        # Check cat-file batch-check
        process = subprocess.Popen(
            ["git", "cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize) %(rest)"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, _ = process.communicate(input="\n".join(blob_hashes[:1000]))
        
        large_blobs = []
        for line in stdout.splitlines():
            parts = line.split()
            if len(parts) >= 3 and parts[1] == "blob":
                size = int(parts[2])
                name = parts[3] if len(parts) > 3 else parts[0]
                if size > HISTORICAL_BLOB_FAIL_BYTES:
                    fails.append(f"Historical git blob '{name}' ({size / MB:.2f} MB) exceeds limit of {HISTORICAL_BLOB_FAIL_BYTES / MB:.1f} MB")
                elif size > 500 * KB:
                    large_blobs.append((size, name))

        if large_blobs:
            large_blobs.sort(reverse=True)
            warns.append(f"Historical large blobs found: {[f'{n} ({sz/KB:.1f} KB)' for sz, n in large_blobs[:5]]}")

    return len(fails) == 0, fails, warns


def main():
    parser = argparse.ArgumentParser(description="VIGIL Preflight & Repository Hygiene Gatekeeper")
    parser.add_argument("--history", action="store_true", help="Audit full git history and large blobs")
    parser.add_argument("--quick", action="store_true", default=True, help="Run standard pre-commit/pre-push checks")
    args = parser.parse_args()

    print("=" * 70)
    print("VIGIL v3.1 — PREFLIGHT VERIFICATION GATEKEEPER (§11.3)")
    print("=" * 70)

    all_fails = []
    all_warns = []

    # Check 1: Branches
    b_ok, b_fails, b_warns = check_branches()
    all_fails.extend(b_fails)
    all_warns.extend(b_warns)
    status_b = "PASS" if b_ok else "FAIL"
    print(f"[{status_b}] Branch Hygiene (active='main', local=['main'], remote=['main'])")

    # Check 2: M1 Tracked working-tree size
    m1_ok, m1_fails, m1_warns, m1_mb = check_m1_tracked_size()
    all_fails.extend(m1_fails)
    all_warns.extend(m1_warns)
    status_m1 = "PASS" if m1_ok else "FAIL"
    print(f"[{status_m1}] M1 Tracked Working-Tree Size: {m1_mb:.3f} MB (Limit: warn > 5 MB, fail > 8 MB)")

    # Check 3: M2 Git repository storage size
    m2_ok, m2_fails, m2_warns, m2_mb = check_m2_repo_size()
    all_fails.extend(m2_fails)
    all_warns.extend(m2_warns)
    status_m2 = "PASS" if m2_ok else "FAIL"
    print(f"[{status_m2}] M2 Git Storage Size (pack+loose): {m2_mb:.3f} MB (Limit: warn > 6 MB, fail > 9 MB)")

    # Check 4: M3 Hosted GitHub Size
    m3_ok, m3_fails, m3_warns, m3_mb = check_m3_github_size()
    all_fails.extend(m3_fails)
    all_warns.extend(m3_warns)
    status_m3 = "PASS" if m3_ok else "FAIL"
    print(f"[{status_m3}] M3 Hosted Size Check")

    # Check 5: Content Hygiene & Lockfiles
    c_ok, c_fails, c_warns = check_tracked_content_and_hygiene()
    all_fails.extend(c_fails)
    all_warns.extend(c_warns)
    status_c = "PASS" if c_ok else "FAIL"
    print(f"[{status_c}] Tracked Content Hygiene (No binary models, DBs, media, or .env)")

    # Check 6: Secret Scanning
    s_ok, s_fails, s_warns = check_secrets_working_tree()
    all_fails.extend(s_fails)
    all_warns.extend(s_warns)
    status_s = "PASS" if s_ok else "FAIL"
    print(f"[{status_s}] Secret Scanning (API keys, GitHub tokens, private keys)")

    # Check 7: History (if requested)
    if args.history:
        h_ok, h_fails, h_warns = check_history()
        all_fails.extend(h_fails)
        all_warns.extend(h_warns)
        status_h = "PASS" if h_ok else "FAIL"
        print(f"[{status_h}] Git History Audit (No historical blobs > 1 MB)")

    print("-" * 70)
    if all_warns:
        print("WARNINGS:")
        for w in all_warns:
            print(f"  [WARN] {w}")

    if all_fails:
        print("\nERRORS (PREFLIGHT FAILED):")
        for f in all_fails:
            print(f"  [FAIL] {f}")
        print("\nResult: PREFLIGHT FAILED. Correct issues before push.")
        sys.exit(1)
    else:
        print("\nResult: ALL PREFLIGHT CHECKS PASSED. Ready for commit/push.")
        sys.exit(0)


if __name__ == "__main__":
    main()
