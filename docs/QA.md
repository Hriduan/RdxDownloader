# v1.0.1 verification

| Check | Result | Scope |
|---|---|---|
| Python backend/security/runtime/release tests | 45 passed | Includes public-IP guards, limits, format selection, direct-media metadata, platform routing, actionable errors and version selection |
| Real synthetic stream integration | Passed | Generated 640×360 video plus tone audio fetched by yt-dlp and locally merged by FFmpeg into MP4 with both tracks |
| Generic direct-media integration | Passed | Own generated direct MP4, locally extracted using the Generic extractor |
| Deno runtime integration | Passed | Actual sandbox invocation; file and network operations denied |
| Git release regression tests | 8 passed, included above | Local bare repos: imported/unrelated history, unborn branch, repeated releases, cancellation, rejected push, normal clone and dry-run |
| Browser fixtures | 95 assertions / 17 cases | 320/390/1440px, light/dark, source formats, quality filtering, missing backend/runtime, backend settings, errors and dialogs |
| Ad fixtures | 34 assertions / 6 cases | Consent, unique placements, no-fill collapse and downloader separation; provider traffic intercepted |
| Source/project audit | Passed | Root index, 12 unique manual ad positions outside downloader, syntax and release-helper checks |
| Visual inspection | Passed | Desktop/mobile helper renders, mobile quality list, runtime checklist, backend settings, dark mode and ad layout |
| Release dry-run | Passed | v1.0.1 planned; no network access, commits, tags or pushes |

Browser source catalogs and jobs are simulated. Real media integration uses only generated local test media; its loopback exception exists only in tests. Production public-network guards remain enabled. No real provider requests, impressions or ad clicks occurred.

Platform tests verify URL routing, not end-to-end public platform downloads. No real Facebook, YouTube, Instagram, Bilibili or TikTok video was downloaded. This does not establish universal compatibility, source-watermark removal, legal permission or production security. Docker builds, physical Android/Termux execution, cloud deployment and pushes to the user's GitHub repository were not performed here.

See [UI-QA.json](UI-QA.json), [AD-QA.json](AD-QA.json) and [BACKEND-QA.json](BACKEND-QA.json). Run the included diagnostics and tests on the actual deployment host.
