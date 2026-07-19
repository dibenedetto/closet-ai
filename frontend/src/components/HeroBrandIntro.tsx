import type { AnimationEvent } from 'react'

import BrandWordmark from './BrandWordmark'
import Logo from './Logo'

type HeroBrandIntroProps = {
  onComplete: () => void
}

/** Lockup introduttivo: da centro pagina raggiunge il brand reale della shell. */
export default function HeroBrandIntro({ onComplete }: HeroBrandIntroProps) {
  function handleAnimationEnd(event: AnimationEvent<HTMLDivElement>) {
    // Le animazioni dei due figli fanno bubbling: chiudiamo l'overlay soltanto
    // quando termina la dissolvenza del contenitore principale.
    if (event.target === event.currentTarget) onComplete()
  }

  return (
    <div
      className="hero-brand-intro"
      data-testid="hero-brand-intro"
      aria-hidden="true"
      onAnimationEnd={handleAnimationEnd}
    >
      <span className="hero-intro-logo"><Logo size={112} /></span>
      <span className="hero-intro-wordmark"><BrandWordmark /></span>
    </div>
  )
}
