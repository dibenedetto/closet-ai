/** Gruccia + foglia: il guardaroba come risorsa da coltivare. */
export default function Logo({ size = 34 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="none"
      aria-hidden="true"
      focusable="false"
    >
      <defs>
        <linearGradient id="closetai-bg" x1="0" y1="0" x2="48" y2="48">
          <stop offset="0%" stopColor="#2e6b52" />
          <stop offset="100%" stopColor="#173d30" />
        </linearGradient>
      </defs>
      {/* tondo di sfondo */}
      <rect x="1" y="1" width="46" height="46" rx="12" fill="url(#closetai-bg)" />
      {/* gruccia */}
      <path
        d="M24 15 L9 30 Q7.5 31.8 9.5 33 L38.5 33 Q40.5 31.8 39 30 L24 15 Z"
        fill="none"
        stroke="#ffffff"
        strokeWidth="2.6"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      {/* gambo dal gancio */}
      <path
        d="M24 15 Q24 11 27 9.5"
        fill="none"
        stroke="#ffffff"
        strokeWidth="2.6"
        strokeLinecap="round"
      />
      {/* foglia che germoglia dal gancio */}
      <path
        d="M27 9.5 Q33 4.5 38 7 Q36.5 13 30.5 12.5 Q28 12 27 9.5 Z"
        fill="#b9d879"
        stroke="#8db756"
        strokeWidth="1"
      />
      {/* nervatura della foglia */}
      <path
        d="M28.5 10.5 Q32.5 8.5 36 7.8"
        fill="none"
        stroke="#527b35"
        strokeWidth="1"
        strokeLinecap="round"
      />
    </svg>
  )
}
