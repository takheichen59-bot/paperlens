// Path definitions from Lucide, ISC license: https://github.com/lucide-icons/lucide
const paths={
 search:'<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
 library:'<path d="m16 6 4 14M12 6v14M8 6v14M4 6v14"/>',
 layers:'<path d="m12 3 10 5-10 5L2 8l10-5ZM2 12l10 5 10-5M2 16l10 5 10-5"/>',
 download:'<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/>',
 upload:'<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12"/>',
 file:'<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8ZM14 2v6h6M8 13h8M8 17h6"/>',
 columns:'<rect width="18" height="18" x="3" y="3" rx="2"/><path d="M12 3v18"/>',
 settings:'<path d="m9.7 4.1.6-2.1h3.4l.6 2.1 2.1 1.2 2.1-.5 1.7 2.9-1.5 1.6v2.4l1.5 1.6-1.7 2.9-2.1-.5-2.1 1.2-.6 2.1h-3.4l-.6-2.1-2.1-1.2-2.1.5-1.7-2.9 1.5-1.6V9.3L4.4 7.7l1.7-2.9 2.1.5Z"/><circle cx="12" cy="10.5" r="3"/>',
 lock:'<rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V6a4 4 0 0 1 8 0v4"/>',
 user:'<circle cx="12" cy="8" r="4"/><path d="M4 21v-2a6 6 0 0 1 6-6h4a6 6 0 0 1 6 6v2"/>',
 menu:'<path d="M4 6h16M4 12h16M4 18h16"/>',
 arrow:'<path d="M5 12h14m-6-6 6 6-6 6"/>',
 back:'<path d="M19 12H5m6-6-6 6 6 6"/>',
 external:'<path d="M15 3h6v6m-6 0 6-6M10 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-5"/>',
 check:'<path d="m20 6-11 11-5-5"/>',
 circleCheck:'<circle cx="12" cy="12" r="10"/><path d="m8 12 3 3 5-6"/>',
 clock:'<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
 info:'<circle cx="12" cy="12" r="10"/><path d="M12 16v-4m0-4h.01"/>',
 chevron:'<path d="m9 18 6-6-6-6"/>',
 close:'<path d="m18 6-12 12M6 6l12 12"/>',
 pause:'<path d="M9 4v16M15 4v16"/>',
 play:'<path d="m6 3 15 9-15 9Z"/>',
 refresh:'<path d="M3 11a9 9 0 0 1 15.4-6.4L21 7M21 3v4h-4M21 13a9 9 0 0 1-15.4 6.4L3 17m0 4v-4h4"/>',
 quote:'<path d="M3 7h6v6H3Zm0 6c0 4 2 5 5 5M15 7h6v6h-6Zm0 6c0 4 2 5 5 5"/>',
 bookmark:'<path d="M19 21l-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2Z"/>',
 edit:'<path d="m16 3 5 5M3 21l4-1L21 6a2 2 0 0 0-4-4L3 16Z"/>',
 help:'<circle cx="12" cy="12" r="10"/><path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3m.1 4h.01"/>'
};
export const icon=(name)=>`<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name]||paths.file}</svg>`;
export function mountIcons(root=document){for(const el of root.querySelectorAll('[data-icon]'))el.innerHTML=icon(el.dataset.icon);}
