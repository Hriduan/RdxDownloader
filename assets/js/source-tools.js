/* Browser-only link hints. Backend extractors and access rules determine actual availability. */
window.RDX_SOURCE_TOOLS=Object.freeze({
  linkFromText(text){const match=String(text||'').match(/https?:\/\/[^\s<>"“”]+/i);return match?match[0].replace(/[),;!。]+$/,''):String(text||'').trim()},
  family(value){try{const host=new URL(value).hostname.toLowerCase();for(const [name,hosts] of [['YouTube',['youtube.com','youtu.be','youtube-nocookie.com']],['Facebook',['facebook.com','fb.watch','fb.com']],['Instagram',['instagram.com','instagr.am']],['Bilibili',['bilibili.com','b23.tv','bilibili.tv']],['TikTok',['tiktok.com']]])if(hosts.some(h=>host===h||host.endsWith('.'+h)))return name;return 'Other source / direct media'}catch{return ''}}
});
