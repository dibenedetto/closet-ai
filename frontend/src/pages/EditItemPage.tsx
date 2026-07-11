import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import Icon from '../components/Icon'
import ItemImage from '../components/ItemImage'
import PageHeader from '../components/PageHeader'
import { ErrorView, LoadingView } from '../components/StateView'
import { errorMessage } from '../api/client'
import { getItem, itemImageUrl, updateItem, type Item } from '../api/items'

export default function EditItemPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const itemId = Number(id)
  const [item, setItem] = useState<Item | null>(null)
  const [name, setName] = useState('')
  const [category, setCategory] = useState('')
  const [color, setColor] = useState('')
  const [price, setPrice] = useState('')
  const [purchaseDate, setPurchaseDate] = useState('')
  const [loadingError, setLoadingError] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!Number.isInteger(itemId) || itemId < 1) {
      setLoadingError('L’identificativo del capo non è valido.')
      return
    }
    getItem(itemId)
      .then((value) => {
        setItem(value)
        setName(value.name)
        setCategory(value.category ?? '')
        setColor(value.color ?? '')
        setPrice(value.price != null ? String(value.price) : '')
        setPurchaseDate(value.purchase_date ?? '')
      })
      .catch((reason: unknown) => setLoadingError(errorMessage(reason)))
  }, [itemId])

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!item || saving) return
    setSaving(true)
    setError(null)
    try {
      await updateItem(item.id, {
        name: name.trim(),
        category: category.trim() || null,
        color: color.trim() || null,
        price: price ? Number(price) : null,
        purchase_date: purchaseDate || null,
      })
      navigate(`/items/${item.id}`, { replace: true })
    } catch (reason: unknown) {
      setError(errorMessage(reason))
      setSaving(false)
    }
  }

  if (loadingError) {
    return <ErrorView message={loadingError} action={<Link to="/" className="button button-primary">Torna al guardaroba</Link>} />
  }
  if (!item) return <LoadingView label="Carico i dettagli del capo…" />

  return (
    <section>
      <PageHeader
        eyebrow={`Capo #${item.id}`}
        title="Correggi i dettagli."
        description="Un guardaroba accurato rende più affidabili outfit, gap analysis e cost-per-wear."
        actions={<Link to={`/items/${item.id}`} className="button button-secondary"><Icon name="arrow-left" size={17} /> Dettaglio capo</Link>}
      />

      <form className="editor-layout" onSubmit={onSubmit}>
        <section className="editor-card">
          <div className="form-section-heading">
            <span className="form-section-number"><Icon name="camera" size={14} /></span>
            <div><h2>Foto originale</h2><p>Usata per classificazione e riconoscimento visivo.</p></div>
          </div>
          <div className="upload-zone has-image" style={{ pointerEvents: 'none' }}>
            <ItemImage src={itemImageUrl(item.id)} alt={item.name} loading="eager" />
          </div>
          <div className="analysis-note">
            <Icon name="wand" size={19} />
            <p><strong>Vuoi rianalizzare la foto?</strong>Dal dettaglio del capo puoi chiedere una nuova classificazione automatica.</p>
          </div>
        </section>

        <section className="editor-card">
          <div className="form-section">
            <div className="form-section-heading">
              <span className="form-section-number">1</span>
              <div><h2>Identità del capo</h2><p>Puoi correggere ciò che la classificazione non ha colto.</p></div>
            </div>
            <div className="form-grid">
              <label className="field field-wide" htmlFor="edit-name">
                Nome del capo *
                <input id="edit-name" type="text" required maxLength={200} value={name} onChange={(event) => setName(event.target.value)} />
              </label>
              <label className="field" htmlFor="edit-category">
                Categoria
                <input id="edit-category" type="text" maxLength={64} value={category} onChange={(event) => setCategory(event.target.value)} placeholder="Es. camicia" />
              </label>
              <label className="field" htmlFor="edit-color">
                Colore
                <input id="edit-color" type="text" maxLength={32} value={color} onChange={(event) => setColor(event.target.value)} placeholder="Es. blu" />
              </label>
            </div>
          </div>

          <div className="form-section">
            <div className="form-section-heading">
              <span className="form-section-number">2</span>
              <div><h3>Storia di acquisto</h3><p>Questi dati alimentano valore d’uso e cost-per-wear.</p></div>
            </div>
            <div className="form-grid">
              <label className="field" htmlFor="edit-price">
                Prezzo di acquisto (€)
                <input id="edit-price" type="number" min={0} step="0.01" inputMode="decimal" value={price} onChange={(event) => setPrice(event.target.value)} />
              </label>
              <label className="field" htmlFor="edit-date">
                Data di acquisto
                <input id="edit-date" type="date" value={purchaseDate} onChange={(event) => setPurchaseDate(event.target.value)} />
              </label>
            </div>
          </div>

          {error && <div className="error" role="alert"><Icon name="circle-alert" size={18} /> {error}</div>}

          <div className="form-actions">
            <span className="required-note">Lascia vuoti i campi facoltativi per rimuoverli.</span>
            <div className="button-row">
              <Link to={`/items/${item.id}`} className="button button-secondary">Annulla</Link>
              <button type="submit" disabled={saving}>
                {saving ? 'Salvo…' : <><Icon name="check" size={17} /> Salva modifiche</>}
              </button>
            </div>
          </div>
        </section>
      </form>
    </section>
  )
}
