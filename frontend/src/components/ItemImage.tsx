import { useState } from 'react'

import Icon from './Icon'

export default function ItemImage({
  src,
  alt,
  className = '',
  loading = 'lazy',
}: {
  src?: string | null
  alt: string
  className?: string
  loading?: 'eager' | 'lazy'
}) {
  const [failed, setFailed] = useState(false)

  if (!src || failed) {
    return (
      <div className={`item-image-fallback ${className}`} role="img" aria-label={`Immagine non disponibile per ${alt}`}>
        <Icon name="shirt" size={30} />
        <span>Immagine non disponibile</span>
      </div>
    )
  }

  return (
    <img
      className={className}
      src={src}
      alt={alt}
      loading={loading}
      onError={() => setFailed(true)}
    />
  )
}
