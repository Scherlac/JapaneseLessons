#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Migrates the JapaneseLessons project from flat-root layout to jlesson/ package.

.DESCRIPTION
    Step 1 of 3 in the project structure migration.
    - Creates jlesson/, jlesson/video/, jlesson/exporters/ directories
    - Adds empty __init__.py files to each
    - Uses git mv to preserve file history for all production modules
    - Cleans up root: removes requirements.txt, progress_report_prev.md; moves structure.md to docs/
    - Commits the structural move as a single git commit (code changes are a separate commit)

.NOTES
    Run from the project root: .\migrate_structure.ps1
    Must be run in an activated conda environment with git available.
    Working tree must be clean before running.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Guard: must be run from project root ───────────────────────────────────
if (-not (Test-Path "pyproject.toml")) {
    Write-Error "Run this script from the project root (where pyproject.toml lives)."
    exit 1
}

# ── Guard: working tree must be clean ──────────────────────────────────────
$status = git status --porcelain
if ($status) {
    Write-Error "Working tree is not clean. Commit or stash changes before running."
    exit 1
}

Write-Host "`n=== Step 1: Create package directory structure ===" -ForegroundColor Cyan

# Create directories (git doesn't track empty dirs, so we create __init__.py files below)
New-Item -ItemType Directory -Path "jlesson"           -Force | Out-Null
New-Item -ItemType Directory -Path "jlesson\video"     -Force | Out-Null
New-Item -ItemType Directory -Path "jlesson\exporters" -Force | Out-Null
Write-Host "  Created: jlesson/, jlesson/video/, jlesson/exporters/"

# ── Write __init__.py files ─────────────────────────────────────────────────

$rootInit = @'
"""
jlesson — Japanese lesson generator package.
"""
'@
Set-Content -Path "jlesson\__init__.py"          -Value $rootInit          -Encoding UTF8 -NoNewline
Set-Content -Path "jlesson\video\__init__.py"    -Value '"""jlesson.video — video production sub-package."""' -Encoding UTF8 -NoNewline
Set-Content -Path "jlesson\exporters\__init__.py" -Value '"""jlesson.exporters — export adapter sub-package."""' -Encoding UTF8 -NoNewline
Write-Host "  Created: jlesson/__init__.py, jlesson/video/__init__.py, jlesson/exporters/__init__.py"

Write-Host "`n=== Step 2: git mv production modules ===" -ForegroundColor Cyan

# Core modules → jlesson/
git mv generate_lesson.py  jlesson/cli.py
git mv curriculum.py       jlesson/curriculum.py
git mv config.py           jlesson/config.py
git mv prompt_template.py  jlesson/prompt_template.py
git mv vocab_generator.py  jlesson/vocab_generator.py
git mv llm_client.py       jlesson/llm_client.py
Write-Host "  Moved core modules → jlesson/"

# Video modules → jlesson/video/
git mv tts_engine.py  jlesson/video/tts_engine.py
git mv video_cards.py jlesson/video/cards.py
git mv video_builder.py jlesson/video/builder.py
Write-Host "  Moved video modules → jlesson/video/"

# Stage new __init__.py files
git add jlesson/__init__.py
git add jlesson/video/__init__.py
git add jlesson/exporters/__init__.py
Write-Host "  Staged __init__.py files"

Write-Host "`n=== Step 3: Clean up root ====" -ForegroundColor Cyan

# Move structure.md into docs/
git mv structure.md docs/structure.md
Write-Host "  Moved: structure.md → docs/structure.md"

# Remove redundant files
git rm requirements.txt
Write-Host "  Removed: requirements.txt"

git rm progress_report_prev.md
Write-Host "  Removed: progress_report_prev.md"

Write-Host "`n=== Step 4: Commit structural move ===" -ForegroundColor Cyan

$commitMessage = @"
refactor: reorganise project into jlesson/ package

Move all production Python modules into jlesson/ package
to replace the flat root layout with a proper importable package.

- jlesson/cli.py          <- generate_lesson.py
- jlesson/curriculum.py   <- curriculum.py
- jlesson/config.py       <- config.py
- jlesson/prompt_template.py
- jlesson/vocab_generator.py
- jlesson/llm_client.py
- jlesson/video/tts_engine.py  <- tts_engine.py
- jlesson/video/cards.py       <- video_cards.py
- jlesson/video/builder.py     <- video_builder.py
- Add jlesson/__init__.py, jlesson/video/__init__.py, jlesson/exporters/__init__.py
- docs/structure.md  <- structure.md (moved to docs/)
- Removed: requirements.txt (redundant), progress_report_prev.md (archived)

Code-level changes (import fixes, pyproject.toml, tests) follow in a
separate commit so this commit shows only the structural move.
"@

git commit -m $commitMessage
Write-Host "`n✓ Structural move committed." -ForegroundColor Green
Write-Host "  Next: run step 2 to fix imports, pyproject.toml, tests, and documentation." -ForegroundColor Yellow

git log --oneline -3
