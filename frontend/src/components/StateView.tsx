import type { ReactNode } from 'react'

import Icon from './Icon'

export function LoadingView({ label = 'Sto preparando i dati…' }: { label?: string }) {
  return (
    <div className="state-view loading-view" role="status" aria-live="polite">
      <span className="loading-orbit" aria-hidden="true" />
      <strong>{label}</strong>
      <span>Ci vorrà solo un momento.</span>
    </div>
  )
}

export function ErrorView({
  title = 'Qualcosa non ha funzionato',
  message,
  action,
}: {
  title?: string
  message: string
  action?: ReactNode
}) {
  return (
    <div className="state-view error-view" role="alert">
      <span className="state-icon"><Icon name="circle-alert" size={22} /></span>
      <div>
        <strong>{title}</strong>
        <p>{message}</p>
        {action && <div className="state-action">{action}</div>}
      </div>
    </div>
  )
}

export function EmptyView({
  icon = 'hanger',
  title,
  message,
  action,
}: {
  icon?: 'hanger' | 'search' | 'sparkles'
  title: string
  message: string
  action?: ReactNode
}) {
  return (
    <div className="state-view empty-view">
      <span className="state-icon"><Icon name={icon} size={24} /></span>
      <div>
        <strong>{title}</strong>
        <p>{message}</p>
        {action && <div className="state-action">{action}</div>}
      </div>
    </div>
  )
}
