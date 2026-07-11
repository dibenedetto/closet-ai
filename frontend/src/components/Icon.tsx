import type { ReactNode, SVGProps } from 'react'

export type IconName =
  | 'arrow-left'
  | 'arrow-right'
  | 'calendar'
  | 'camera'
  | 'check'
  | 'chevron-right'
  | 'circle-alert'
  | 'clock'
  | 'close'
  | 'edit'
  | 'euro'
  | 'flask'
  | 'gap'
  | 'grid'
  | 'hanger'
  | 'heart'
  | 'leaf'
  | 'menu'
  | 'palette'
  | 'plus'
  | 'recycle'
  | 'refresh'
  | 'search'
  | 'shirt'
  | 'sparkles'
  | 'tag'
  | 'trash'
  | 'trend'
  | 'wand'
  | 'wrench'

interface IconProps extends Omit<SVGProps<SVGSVGElement>, 'name'> {
  name: IconName
  size?: number
}

export default function Icon({ name, size = 20, ...props }: IconProps) {
  const common = {
    width: size,
    height: size,
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: 1.8,
    strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const,
    'aria-hidden': true,
    focusable: false,
    ...props,
  }

  const paths: Record<IconName, ReactNode> = {
    'arrow-left': <><path d="m15 18-6-6 6-6" /><path d="M9 12h10" /></>,
    'arrow-right': <><path d="m9 18 6-6-6-6" /><path d="M5 12h10" /></>,
    calendar: <><rect x="3" y="5" width="18" height="16" rx="2" /><path d="M16 3v4M8 3v4M3 10h18" /></>,
    camera: <><path d="M14.5 4 16 7h3a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2h3l1.5-3z" /><circle cx="12" cy="13" r="4" /></>,
    check: <path d="m5 12 4 4L19 6" />,
    'chevron-right': <path d="m9 18 6-6-6-6" />,
    'circle-alert': <><circle cx="12" cy="12" r="9" /><path d="M12 8v5M12 16h.01" /></>,
    clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
    close: <path d="m6 6 12 12M18 6 6 18" />,
    edit: <><path d="M12 20h9" /><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4z" /></>,
    euro: <><path d="M18 7.5a6 6 0 1 0 0 9" /><path d="M5 10h9M5 14h8" /></>,
    flask: <><path d="M9 3h6M10 3v6l-5 9a2 2 0 0 0 1.8 3h10.4A2 2 0 0 0 19 18l-5-9V3" /><path d="M8 15h8" /></>,
    gap: <><path d="M4 4v6h6V4zM14 4v6h6V4zM4 14v6h6v-6z" /><path d="M17 14v6M14 17h6" /></>,
    grid: <><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /></>,
    hanger: <><path d="M12 7a2 2 0 1 1 2-2" /><path d="m12 7-9 8a2 2 0 0 0 1.4 3.5h15.2A2 2 0 0 0 21 15z" /></>,
    heart: <path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.6l-1-1a5.5 5.5 0 0 0-7.8 7.8l1 1L12 21l7.8-7.6 1-1a5.5 5.5 0 0 0 0-7.8z" />,
    leaf: <><path d="M20 4c-8 0-14 4-14 10a6 6 0 0 0 6 6c6 0 8-8 8-16Z" /><path d="M4 21c3-6 7-9 12-12" /></>,
    menu: <path d="M4 7h16M4 12h16M4 17h16" />,
    palette: <><path d="M12 3a9 9 0 0 0 0 18h1.5a2 2 0 0 0 0-4H12a2 2 0 0 1 0-4h5a4 4 0 0 0 4-4c0-3.3-4-6-9-6Z" /><circle cx="7.5" cy="10" r=".7" fill="currentColor" stroke="none" /><circle cx="10" cy="6.8" r=".7" fill="currentColor" stroke="none" /><circle cx="14" cy="6.5" r=".7" fill="currentColor" stroke="none" /></>,
    plus: <path d="M12 5v14M5 12h14" />,
    recycle: <><path d="m7 19-3-5 3-5" /><path d="M4 14h7M10 5h6l3 5M16 2l3 3-3 3M17 19h-6l-3-5M8 22l-3-3 3-3" /></>,
    refresh: <><path d="M20 6v5h-5" /><path d="M4 18v-5h5" /><path d="M18 9a7 7 0 0 0-12-2M6 15a7 7 0 0 0 12 2" /></>,
    search: <><circle cx="11" cy="11" r="7" /><path d="m20 20-4-4" /></>,
    shirt: <><path d="m8 4 4 2 4-2 5 3-2 5-3-1v9H8v-9l-3 1-2-5z" /><path d="M9 4a3 3 0 0 0 6 0" /></>,
    sparkles: <><path d="m12 3 1.2 3.8L17 8l-3.8 1.2L12 13l-1.2-3.8L7 8l3.8-1.2z" /><path d="m19 14 .7 2.3L22 17l-2.3.7L19 20l-.7-2.3L16 17l2.3-.7zM5 14l.6 1.8 1.8.6-1.8.6L5 19l-.6-1.8-1.8-.6 1.8-.6z" /></>,
    tag: <><path d="M20 13 13 20l-9-9V4h7z" /><circle cx="8" cy="8" r="1" /></>,
    trash: <><path d="M4 7h16M9 7V4h6v3M6 7l1 14h10l1-14M10 11v6M14 11v6" /></>,
    trend: <><path d="M4 18 10 12l4 4 6-9" /><path d="M15 7h5v5" /></>,
    wand: <><path d="m15 4 5 5L8 21H3v-5z" /><path d="m13 6 5 5M6 4v3M4.5 5.5h3M19 15v4M17 17h4" /></>,
    wrench: <><path d="M14.7 6.3a4 4 0 0 0-5-5L12 3.6 8.5 7.1 6.2 4.8a4 4 0 0 0 5 5L18.5 17a2.1 2.1 0 0 1-3 3l-7.3-7.3a4 4 0 0 1-5-5l2.3 2.3L9 6.5 6.7 4.2" /></>,
  }

  return <svg {...common}>{paths[name]}</svg>
}
