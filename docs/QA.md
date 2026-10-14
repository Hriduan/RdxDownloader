# v1.0.2 connected-hosting verification

| Check | Result | Scope |
|---|---|---|
| Python backend/runtime/release tests | 53 passed | Includes direct top-level media, no-prompt wrapper, generated fixture and earlier security/release regressions |
| UI fixtures | 95 assertions / 17 cases | Layouts, quality filtering, dialogs, failure states and backend settings; simulated catalogs/jobs |
| Ad fixtures | 34 assertions / 6 cases | Intercepted providers, no real impressions or clicks |
| Live Render health | Passed | Real HTTPS response; all backend dependencies reported present |
| Live CORS | Passed | Allows https://hriduan.github.io |
| Live inspection → job → file | Passed | Original generated 2-second H.264/AAC MP4 fetched from this repository |
| Downloaded media validation | Passed | 320×180 video and audio tracks; 22,105 bytes; byte-for-byte same as original |
| Cloud deployment | Performed | Render Docker Free, linked to this repository's main; GitHub connection restricted to this repo |
| Repository publication | Performed | Reviewed browser commits; no force pushes or credentials stored in project |

A hosted test revealed that direct media can have no formats list. The worker now safely handles an eligible top-level media record, while retaining DRM/protocol checks. The successful live test was repeated after deploying that fix.

These tests do not establish that Facebook, YouTube, Instagram, Bilibili or TikTok will accept every source or datacenter IP. No real third-party platform media was downloaded. Physical Termux setup was not tested. Free hosting can sleep, restart or suspend at quotas; temporary jobs/files disappear on deploy/restart. No 24/7, unlimited bandwidth, error-free, universal support or source-watermark-removal promise is made.

See LIVE-DEPLOYMENT-QA.json for the actual HTTPS test and UI-QA.json / AD-QA.json for browser fixtures. No private download capability is included in the report.
