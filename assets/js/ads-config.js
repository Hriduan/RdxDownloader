/* PUBLIC ad configuration. Register RdxDownloader's actual domain with each provider.
   Do NOT reuse keys registered only to technogalaxy.tech. No real units are invented.
   See docs/ADVERTISING.md. Keep Google Auto ads / overlays OFF to protect the tool. */
window.RDX_ADS = {
  enabled: false,
  version: 'rdx-ads-v1',
  google: { enabled: false, client: '', requireCmp: true, slots: {
    'after-downloader': '', 'steps-left': '', 'steps-middle': '', 'steps-right': '',
    'after-platforms': '', 'quality-left': '', 'quality-middle': '', 'quality-right': '',
    'after-faq': '', 'footer-left': '', 'footer-middle': '', 'footer-right': ''
  } },
  adsterra: { enabled: false, approvedHosts: ['bicea.org','www.highperformanceformat.com','www.profitabledisplaynetwork.com'], slots: {
    /* 'steps-left': {kind:'banner',key:'YOUR_32_HEX_KEY',scriptUrl:'https://approved-host/KEY/invoke.js',width:300,height:250},
       'after-platforms': {kind:'native',key:'YOUR_32_HEX_KEY',scriptUrl:'https://bicea.org/21/KEY',containerId:'container-KEY'} */
  } }
};
