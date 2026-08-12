---
title: ue-plugin-installation
description: Install third-party UE plugins (GitHub open-source, marketplace, project vs engine level). Covers feasibility research, download, submodule handling, registration, build verification, and MCP registration for UE-facing tools.
---

# UE Plugin Installation

Install third-party UE plugins into a project. Two levels: **Project plugin** (`Plugins/<Name>/` — travels with repo) and **Engine plugin** (`Engine/Plugins/<Name>/` — all projects on that engine install).

## Workflow

### 1. Feasibility Research

Check via GitHub API (fast, no full page load):

```bash
# Repo metadata — stars, license, last update, description
curl -sL "https://api.github.com/repos/<owner>/<repo>"

# Check releases for supported engine versions
curl -sL "https://api.github.com/repos/<owner>/<repo>/releases?per_page=5"

# Check .uplugin for engine version and module list
curl -sL "https://raw.githubusercontent.com/<owner>/<repo>/<branch>/<Name>.uplugin"

# Check submodules requirement
curl -sL "https://raw.githubusercontent.com/<owner>/<repo>/<branch>/.gitmodules"
```

**Key signals:**
- Stars: >50 = community tested; >300 = well-vetted
- License: MIT/Apache-2.0/MPL-2.0 = free for commercial; check terms
- Last update: within 6 months = actively maintained
- EngineVersion in .uplugin: empty string = no version lock; specific = may need matching engine
- Tags/releases exist = easier install; no releases = build from source

### 2. Download via gh-proxy (slow network fallback)

When `https://github.com/` downloads are slow, prefix with gh-proxy:

```bash
curl -sL -o plugin.zip "https://gh-proxy.com/https://github.com/<owner>/<repo>/archive/refs/heads/main.zip"
```

For tagged releases:
```bash
curl -sL -o plugin.zip "https://gh-proxy.com/https://github.com/<owner>/<repo>/archive/refs/tags/v1.0.0.zip"
```

### 3. Handle Submodules

Check `.gitmodules` in the repo for submodule dependencies. Download each separately:

```bash
# For each submodule: url + path
curl -sL -o submodule.zip "https://gh-proxy.com/https://github.com/<owner>/<subrepo>/archive/refs/heads/main.zip"
unzip -qo submodule.zip
# ⚠️ Fix nested directory: archive extracts as SubRepo-main/ inside SubRepo/
# Move contents up one level if this happens
if [ -d "Source/SubRepo/SubRepo-main" ]; then
  mv Source/SubRepo/SubRepo-main/* Source/SubRepo/
  rmdir Source/SubRepo/SubRepo-main
fi
```

### 4. Install to Project

```bash
# Extract to project Plugins/
unzip -qo plugin.zip -d /tmp/plugin-tmp
mv /tmp/plugin-tmp/Repo-BranchOrTag/ Plugins/<PluginName>/
rm -rf /tmp/plugin-tmp plugin.zip
```

**Naming:** The directory name doesn't matter for UE — it resolves by .uplugin filename. But keep it clean (repo name or friendly name).

### 5. Register in .uproject

```json
{
  "Plugins": [
    {"Name": "<UPluginFilename>", "Enabled": true}
  ]
}
```

The `Name` must match the `.uplugin` filename (without extension). Patch the existing .uproject using `patch` tool — add the entry in the `Plugins` array.

### 6. Build to Verify

```bash
cd "<ProjectDir>"
"<EngineDir>/Engine/Build/BatchFiles/Build.bat" <ProjectName>Editor Win64 Development \
  -Project="<ProjectDir>/<Project>.uproject" -Progress 2>&1 | tail -10
```

**Signs of success:**
- `Compile [x64] <Module>.cpp` entries for the plugin's modules
- `Link [x64] UnrealEditor-<Module>.dll`
- `Result: Succeeded`

**Signs of failure:**
- `ERROR: ... is not compatible with the current engine version` — engine mismatch
- `LNK2019` / `LNK2001` — missing dependency module, add to Build.cs or .uplugin dependencies
- `Cannot open include file` — missing submodule or include path issue
- `Target is up to date` with 0 new compilations — plugin may not have been detected (check .uproject entry, file paths)

If "Target is up to date" but plugin was just added, touch the .uplugin to force re-evaluation:
```bash
touch "Plugins/<Name>/<Name>.uplugin"
```

### 7. (Optional) Hermes MCP Registration

If the plugin provides an MCP server (e.g. FlopAI UnrealMCP), register it with Hermes:

```bash
hermes mcp add <server-name> \
  --command <command> \
  --args --directory "<PythonDir>" run <script.py>

# Handle interactive "Enable all N tools?" prompt by piping Y
echo "Y" | hermes mcp add ...
```

The server must be running before Hermes can use its tools.

## Pitfalls

- **Submodule nested directory:** GitHub zip archives extract as `RepoName-main/` — if you extract into a directory that already has a nested folder with the same name, check and move contents up.
- **Engine version lock in .uplugin:** Some plugins pin an EngineVersion. If empty string (`""`), they usually work across versions. If pinned, may need manual UE5.x compatibility edits.
- **Content-only plugins (no Source/):** No C++ compilation needed — just drop in Plugins/ and register in .uproject.
- **MSYS2 git-bash path quirks:** When running Build.bat from git-bash, some MSYS2 path conversions may affect `/c/` paths. Use absolute Windows paths with drive letters (e.g. `E:/UE_5.7/...`).
- **Plugin conflicts:** Two plugins registering the same module name cause a build error. Check existing plugins before adding new ones.
- **Third-party DLL dependencies:** Some plugins ship with .dll files that must be in the executable path. Check plugin docs for redist requirements.

## Verification

After installation, open the project in UE Editor and check:
- Edit → Plugins → search for plugin name → should show Enabled ✓
- Window menu should show the plugin's panel if it provides one
- Build output should show the plugin's modules

## Related Skills

- **ue-module-build-system** — Build.cs, .uplugin structure, creating your own plugins
