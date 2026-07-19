import logoUrl from '../../logo.svg?url'

/** Logo ufficiale fornito in `frontend/logo.svg`. */
export default function Logo({ size = 34 }: { size?: number }) {
  return (
    <span
      aria-hidden="true"
      style={{
        width: size,
        height: size,
        display: 'inline-grid',
        placeItems: 'center',
        flex: '0 0 auto',
        overflow: 'hidden',
      }}
    >
      <img
        src={logoUrl}
        alt=""
        width={size}
        height={size}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'contain',
        }}
      />
    </span>
  )
}
