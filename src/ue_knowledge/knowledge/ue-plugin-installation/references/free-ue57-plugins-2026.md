# Free UE5.7 Plugins Survey (July 2026)

Surveyed during a UE 5.7 production project session. GitHub API + README + uplugin + build verification.

## Confirmed Free/Open-Source, UE5.7 Compatible

| Plugin | License | Stars | UE5.7 | Last Update | Install Effort |
|--------|---------|-------|-------|-------------|----------------|
| **ActorIO** v1.7.2 | Apache-2.0 | ★306 | ✅ v1.7.2 supports 5.4-5.8 | 2026-07-03 | Low (zip → extract → register) |
| **UnrealMCP/FlopAI** (local) | MIT (repo still OSS) | ★1052 | ✅ 5.5+ | 2026-07-03 (repo now owned by Aura) | Low (zip + git clone) |
| **MapUtils** (ue-map-utils) | MIT | ★1 (new) | ✅ badge in README | 2026-06-23 | Low (zip → extract → register) |
| **GradientspaceUEToolbox** | MPL-2.0 | ★54 | ✅ engine version empty | 2026-06-04 | Medium (3 submodules) |

## Free but Needs API Key

| Plugin | License | Stars | Notes |
|--------|---------|-------|-------|
| **Unreal-Agent** (TREE-Ind) | Apache-2.0 | ★225 | Editor UI free; AI features need GPT API key |

## Not Free / Not Verified

| Tool | Reason |
|------|--------|
| Blockout Tools | Fab commercial plugin |
| HammUEr | itch.io commercial; page unreachable |
| Aura (FlopAI hosted) | Cloud service; pricing page 404 |
| "UE5.7 AI Assistant" | No evidence found — 0 GitHub hits, Epic docs 403, Reddit 0 matches |

## gh-proxy Mirror

Used for all GitHub downloads during this session (user on mobile hotspot with 40KB/s–1.8MB/s):

```
https://gh-proxy.com/https://github.com/<owner>/<repo>/...
```

## Submodule Dependencies (UEToolbox)

UEToolboxPlugin has 3 git submodules requiring separate download:
- `gradientspace/GradientspaceCore`
- `gradientspace/GradientspaceIO`
- `gradientspace/GradientspaceGrid`

Each ~170–300KB. Extract → check for nested `*main/` dir → move up.
