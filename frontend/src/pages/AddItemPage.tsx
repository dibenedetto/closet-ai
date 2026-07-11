import { useEffect, useRef, useState, type ChangeEvent, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import Icon from '../components/Icon'
import PageHeader from '../components/PageHeader'
import { errorMessage } from '../api/client'
import { createItem } from '../api/items'

const MAX_FILE_SIZE = 10 * 1024 * 1024
const ALLOWED_TYPES = new Set(['image/jpeg', 'image/png', 'image/webp'])

export default function AddItemPage() {
  const navigate = useNavigate()
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const [name, setName] = useState('')
  const [category, setCategory] = useState('')
  const [color, setColor] = useState('')
  const [price, setPrice] = useState('')
  const [purchaseDate, setPurchaseDate] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!file) {
      setPreviewUrl(null)
      return
    }
    const url = URL.createObjectURL(file)
    setPreviewUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [file])

  function onFileChange(event: ChangeEvent<HTMLInputElement>) {
    const next = event.target.files?.[0] ?? null
    setError(null)
    if (!next) {
      setFile(null)
      return
    }
    if (!ALLOWED_TYPES.has(next.type)) {
      setError('Formato non supportato. Usa JPG, PNG o WebP.')
      event.target.value = ''
      return
    }
    if (next.size > MAX_FILE_SIZE) {
      setError('L’immagine supera il limite massimo di 10 MB.')
      event.target.value = ''
      return
    }
    setFile(next)
  }

  function clearImage() {
    setFile(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!file) {
      setError('Aggiungi una foto del capo per continuare.')
      fileInputRef.current?.focus()
      return
    }
    setSubmitting(true)
    setError(null)
    try {
      const item = await createItem({
        name: name.trim(),
        category: category.trim() || undefined,
        color: color.trim() || undefined,
        price: price ? Number(price) : undefined,
        purchase_date: purchaseDate || undefined,
        image: file,
      })
      navigate(`/items/${item.id}`, { replace: true })
    } catch (e: unknown) {
      setError(errorMessage(e))
      setSubmitting(false)
    }
  }

  return (
    <section>
      <PageHeader
        eyebrow="Nuovo capo · 1 di 1"
        title="Porta un capo nel tuo guardaroba."
        description="Una foto basta: ClosetAI prova a riconoscere categoria e colore. Tu puoi sempre correggere i dettagli dopo."
        actions={<Link to="/" className="button button-secondary"><Icon name="arrow-left" size={17} /> Guardaroba</Link>}
      />

      <form className="editor-layout" onSubmit={onSubmit} noValidate={false}>
        <section className="editor-card" aria-labelledby="photo-title">
          <div className="form-section-heading">
            <span className="form-section-number">1</span>
            <div>
              <h2 id="photo-title">Fotografa il capo</h2>
              <p>Meglio uno sfondo semplice e luce naturale.</p>
            </div>
          </div>

          <div className={`upload-zone ${previewUrl ? 'has-image' : ''}`}>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              capture="environment"
              required
              aria-label="Scegli una foto del capo"
              aria-describedby="photo-hint"
              onChange={onFileChange}
            />
            {previewUrl ? (
              <img src={previewUrl} alt="Anteprima del nuovo capo" />
            ) : (
              <span className="upload-placeholder">
                <span className="upload-placeholder-icon"><Icon name="camera" size={25} /></span>
                <strong>Scatta o scegli una foto</strong>
                <span id="photo-hint">JPG, PNG o WebP · massimo 10 MB</span>
              </span>
            )}
            {previewUrl && (
              <span className="upload-actions">
                <button type="button" className="button button-small" onClick={(event) => { event.preventDefault(); fileInputRef.current?.click() }}>
                  <Icon name="camera" size={15} /> Cambia foto
                </button>
                <button type="button" className="button button-small" onClick={(event) => { event.preventDefault(); clearImage() }}>
                  <Icon name="trash" size={15} /> Rimuovi
                </button>
              </span>
            )}
          </div>

          <div className="analysis-note">
            <Icon name="wand" size={19} />
            <p><strong>Analisi automatica inclusa</strong>Categoria, colore e stato iniziale vengono stimati dalla foto quando salvi.</p>
          </div>
        </section>

        <section className="editor-card" aria-labelledby="details-title">
          <div className="form-section">
            <div className="form-section-heading">
              <span className="form-section-number">2</span>
              <div>
                <h2 id="details-title">Raccontaci cos’è</h2>
                <p>Il nome è obbligatorio; il resto aiuta statistiche e consigli.</p>
              </div>
            </div>
            <div className="form-grid">
              <label className="field field-wide" htmlFor="item-name">
                Nome del capo <span aria-hidden="true">*</span>
                <input
                  id="item-name"
                  type="text"
                  required
                  maxLength={200}
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  placeholder="Es. T-shirt bordeaux"
                />
                <span className="field-hint">Un nome facile da riconoscere nelle proposte outfit.</span>
              </label>
              <label className="field" htmlFor="item-category">
                Categoria
                <input
                  id="item-category"
                  type="text"
                  maxLength={64}
                  value={category}
                  onChange={(event) => setCategory(event.target.value)}
                  placeholder="Rilevata automaticamente"
                />
              </label>
              <label className="field" htmlFor="item-color">
                Colore
                <input
                  id="item-color"
                  type="text"
                  maxLength={32}
                  value={color}
                  onChange={(event) => setColor(event.target.value)}
                  placeholder="Rilevato automaticamente"
                />
              </label>
            </div>
          </div>

          <div className="form-section">
            <div className="form-section-heading">
              <span className="form-section-number">3</span>
              <div>
                <h3>La storia del capo</h3>
                <p>Serve a calcolare cost-per-wear e durata reale.</p>
              </div>
            </div>
            <div className="form-grid">
              <label className="field" htmlFor="item-price">
                Prezzo di acquisto (€)
                <input
                  id="item-price"
                  type="number"
                  min={0}
                  step="0.01"
                  inputMode="decimal"
                  value={price}
                  onChange={(event) => setPrice(event.target.value)}
                  placeholder="0,00"
                />
              </label>
              <label className="field" htmlFor="item-date">
                Data di acquisto
                <input
                  id="item-date"
                  type="date"
                  value={purchaseDate}
                  onChange={(event) => setPurchaseDate(event.target.value)}
                />
              </label>
            </div>
          </div>

          {error && <div className="error" role="alert"><Icon name="circle-alert" size={18} /> {error}</div>}

          <div className="form-actions">
            <span className="required-note">* Campo obbligatorio</span>
            <div className="button-row">
              <Link to="/" className="button button-secondary">Annulla</Link>
              <button type="submit" className="button button-primary" disabled={submitting}>
                {submitting ? <><span className="loading-orbit" /> Analizzo il capo…</> : <><Icon name="check" size={17} /> Salva nel guardaroba</>}
              </button>
            </div>
          </div>
        </section>
      </form>
    </section>
  )
}
