import wordmarkUrl from '../../name.svg?url'

/** Logotipo ufficiale con nome e payoff, fornito in `frontend/name.svg`. */
export default function BrandWordmark() {
  return (
    <span className="brand-wordmark" aria-hidden="true">
      <img src={wordmarkUrl} alt="" />
    </span>
  )
}
