const Logo = ({ size = 32, showText = true, color = '#fff', style = {} }) => (
  <div style={{ display: 'flex', alignItems: 'center', gap: 10, ...style }}>
    <svg viewBox="0 0 120 120" style={{ height: size, flexShrink: 0 }} role="img" aria-label="Codessy">
      <defs>
        <linearGradient id="logo-blue" x1="22" y1="0" x2="58" y2="36" gradientUnits="userSpaceOnUse">
          <stop stopColor="#35A7FF" /><stop offset="1" stopColor="#2875F0" />
        </linearGradient>
        <linearGradient id="logo-purple" x1="64" y1="0" x2="100" y2="36" gradientUnits="userSpaceOnUse">
          <stop stopColor="#9B5CFF" /><stop offset="1" stopColor="#7340E8" />
        </linearGradient>
        <linearGradient id="logo-green" x1="22" y1="50" x2="58" y2="76" gradientUnits="userSpaceOnUse">
          <stop stopColor="#22D3A6" /><stop offset="1" stopColor="#10B981" />
        </linearGradient>
        <linearGradient id="logo-coral" x1="64" y1="50" x2="100" y2="76" gradientUnits="userSpaceOnUse">
          <stop stopColor="#FF9A55" /><stop offset="1" stopColor="#F45F72" />
        </linearGradient>
      </defs>
      <rect width="120" height="120" rx="28" fill="#070B1F"/>
      <g transform="translate(-1 22)">
        <path d="M22 18C22 8.059 30.059 0 40 0h18v18c0 9.941-8.059 18-18 18H22V18Z" fill="url(#logo-blue)" />
        <circle cx="82" cy="18" r="18" fill="url(#logo-purple)" />
        <path d="M22 40h18c9.941 0 18 8.059 18 18v18H40c-9.941 0-18-8.059-18-18V40Z" fill="url(#logo-green)" />
        <path d="M64 40h18c9.941 0 18 8.059 18 18v18H82c-9.941 0-18-8.059-18-18V40Z" fill="url(#logo-coral)" />
      </g>
    </svg>
    {showText && (
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        <span style={{ fontSize: size * 0.625, fontWeight: 700, letterSpacing: '-0.5px', color }}>Codessy</span>
        {size >= 28 && (
          <span style={{ fontSize: size * 0.3125, fontWeight: 500, letterSpacing: '2px', color: color === '#fff' ? '#94a3b8' : '#5b6572' }}>
            BUILD. AUTOMATE. SCALE.
          </span>
        )}
      </div>
    )}
  </div>
);

export default Logo;
