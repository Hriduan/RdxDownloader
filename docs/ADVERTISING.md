# Advertising without getting in the way

RdxDownloader has **12 responsive manual ad placements**. Every ad is outside the protected `#downloader` section; ads do not move over the input, formats or file-save button. There are no sticky/floating units, popunders, forced redirects, automatic refreshes or click interception. The tool remains usable when optional ads are rejected.

## Placement map

| Zone | Placement IDs | Layout |
|---|---|---|
| After downloader and trust strip | `after-downloader` | Wide |
| After how-it-works content | `steps-left`, `steps-middle`, `steps-right` | Three rectangles desktop; stacked mobile |
| After platforms | `after-platforms` | Wide/native-ready |
| After quality guidance | `quality-left`, `quality-middle`, `quality-right` | Three rectangles desktop; stacked mobile |
| After FAQ | `after-faq` | Wide |
| Before footer | `footer-left`, `footer-middle`, `footer-right` | Three rectangles desktop; stacked mobile |

These are **capacity**, not a recommendation to activate every slot. Google forbids screens with more ads/paid promotion than publisher content and may restrict thin downloader utility sites. Enable a conservative subset first and review current provider policies and source rights. Providing more slots does not promise approval, fill or revenue.

## Why no live ads are embedded yet

The new site's domain and domain-approved publisher/placement codes have not been supplied. Keys registered to technogalaxy.tech should not be copied into this different project without provider authorization. `assets/js/ads-config.js` has both providers disabled and their IDs empty by default. No account approvals or earnings are invented.

To inspect placement spacing locally, append **`?adpreview=1`**. Preview mode renders labeled layout reservations only and never loads ad scripts, even if configured. Normal visitors do not see empty placeholder grids when ads are unconfigured.

## Configure AdSense

1. Register and obtain approval for the actual RdxDownloader domain/site with Google.
2. Create approved **responsive display** units (one shared ID can identify multiple separate elements, but unique IDs provide clearer reporting).
3. In `assets/js/ads-config.js`, set the global `enabled`, `google.enabled`, the `ca-pub-…` client ID and the numeric slot IDs for the positions you choose.
4. Publish Google's genuine **Privacy & messaging/certified CMP** setup. The local choices panel is not a certified CMP and never fabricates consent. Google bootstrap starts paused after explicit local permission; ads resume only on an eligible genuine TCF signal. If your published consent implementation does not expose that signal, Google remains paused. Integrate an appropriate certified provider rather than guessing geographic consent.
5. Add `ads.txt` in your actual hosting root using your provider's exact authorization. On project-path GitHub Pages, serve ads.txt on the actual registrable/custom-domain root as required; a nested repository path is not a replacement. The Python backend and Pages artifact already serve the root ads.txt file; replace its comment with verified provider records.
6. Keep **Auto ads and Google overlay formats disabled in the dashboard** to preserve the manual-layout guarantee. Google may change provider behavior; inspect your real creatives.

Example (replace with your actual approved values; these are not usable IDs):

```js
google: {
  enabled: true,
  client: 'ca-pub-YOUR_16_DIGITS',
  requireCmp: true,
  slots: { 'after-downloader': 'YOUR_NUMERIC_SLOT_ID' }
}
```

## Configure Adsterra

1. Register the new domain and request approved display/native tags.
2. Enable `adsterra.enabled`. Map each intended placement to a provider-approved tag:

```js
adsterra: {
  enabled: true,
  approvedHosts: ['bicea.org'],
  slots: {
    'steps-left': {
      kind: 'banner', key: 'YOUR_32_HEX_KEY',
      scriptUrl: 'https://bicea.org/22/YOUR_32_HEX_KEY', width: 300, height: 250
    },
    'after-platforms': {
      kind: 'native', key: 'ANOTHER_32_HEX_KEY',
      scriptUrl: 'https://bicea.org/21/ANOTHER_32_HEX_KEY',
      containerId: 'container-ANOTHER_32_HEX_KEY'
    }
  }
}
```

Both keys must be real 32-hex provider values. Each supplied key runs once per page to avoid duplicate native container IDs or replaying an unsupported banner tag. Obtain additional placement keys for more simultaneous Adsterra units. The loader accepts the documented bicea paths and original `/KEY/invoke.js` banner paths on explicitly allowed hosts. Do not add an untrusted host. Tags execute in the original page, not a wrapper iframe. Native sizes remain content-driven; verify actual creatives on mobile. A 300px banner is not scaled down into an undersized container.

## Consent, no-fill and testing

- A separate local named choice is required for each network; Google consent is not Adsterra authorization.
- GPC/DNT block optional provider scripts. Choice expires in 180 days. Withdrawal after loading a provider reloads the page because third-party JavaScript cannot reliably be unloaded.
- Google known-unfilled units collapse. Script failures collapse their slots. No timed refresh or aggressive network waterfall is used.
- Google takes priority where both are configured and permitted. Adsterra can serve if Google is not yet eligible. Once a slot starts, it is not refreshed or replaced.
- A loaded script alone is not proof of a filled creative. Adsterra can deliver no ad even after its script loads. No universal no-fill signal is assumed.
- Developer status: `RDX_AD_STATUS()`. This is readiness, not impression reporting.
- Run intercepted browser fixtures for layout and no-overlap checks. Never click your own ads or generate fake ad traffic.

Provider references to review before launch:
- https://support.google.com/adsense/answer/10502938 — publisher policies
- https://support.google.com/adsense/answer/13554116 — consent requirements
- https://adsterra.com/terms/ — provider terms
