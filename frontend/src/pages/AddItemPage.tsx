import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'

import { createItem } from '../api/items'

export default function AddItemPage() {
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [category, setCategory] = useState('')
  const [color, setColor] = useState('')
  const [price, setPrice] = useState('')
  const [purchaseDate, setPurchaseDate] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Genero l'URL di anteprima quando cambia il file e lo revoco al cleanup
  useEffect(() => {
    if (!file) {
      setPreviewUrl(null)
      return
    }
    const url = URL.createObjectURL(file)
    setPreviewUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [file])

  function clearImage() {
    setFile(null)
    const input = document.getElementById('f-img') as HTMLInputElement | null
    if (input) input.value = ''
  }

  async function onSubmit(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault()
    if (!file) {
      setError("Seleziona un'immagine.")
      return
    }
    setError(null)
    setSubmitting(true)
    try {
      const item = await createItem({
        name,
        category: category || undefined,
        color: color || undefined,
        price: price !== '' ? Number(price) : undefined,
        purchase_date: purchaseDate || undefined,
        image: file,
      })
      navigate(`/items/${item.id}`)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
      setSubmitting(false)
    }
  }

  return (
    <section className="panel" style={{ maxWidth: 480 }}>
      <h2 style={{ marginTop: 0 }}>Aggiungi capo</h2>
      <form onSubmit={onSubmit}>
        <label htmlFor="f-name">Nome *</label>
        <input
          id="f-name"
          type="text"
          required
          maxLength={200}
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Es. T-shirt bordeaux"
        />

        <div className="row">
          <div>
            <label htmlFor="f-cat">Categoria</label>
            <input
              id="f-cat"
              type="text"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              placeholder="auto se vuoto"
            />
          </div>
          <div>
            <label htmlFor="f-col">Colore</label>
            <input
              id="f-col"
              type="text"
              value={color}
              onChange={(e) => setColor(e.target.value)}
              placeholder="auto se vuoto"
            />
          </div>
        </div>

        <div className="row">
          <div>
            <label htmlFor="f-price">Prezzo (€)</label>
            <input
              id="f-price"
              type="number"
              min={0}
              step="0.01"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
            />
          </div>
          <div>
            <label htmlFor="f-date">Data acquisto</label>
            <input
              id="f-date"
              type="date"
              value={purchaseDate}
              onChange={(e) => setPurchaseDate(e.target.value)}
            />
          </div>
        </div>

        <label htmlFor="f-img">
          Immagine * <span className="muted">(jpg, png, webp ≤ 10MB)</span>
        </label>
        <input
          id="f-img"
          type="file"
          accept="image/jpeg,image/png,image/webp"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          required
        />

        <div className="preview" aria-live="polite">
          {previewUrl ? (
            <>
              <img src={previewUrl} alt="anteprima" />
              <button type="button" className="clear-img" onClick={clearImage}>
                Rimuovi
              </button>
            </>
          ) : (
            <span>Anteprima immagine</span>
          )}
        </div>

        {error && <p className="error">{error}</p>}

        <div className="actions" style={{ display: 'flex', gap: 8, marginTop: 16 }}>
          <button type="submit" disabled={submitting}>
            {submitting ? 'Carico…' : 'Carica capo'}
          </button>
          <button
            type="button"
            className="ghost"
            onClick={() => navigate(-1)}
            disabled={submitting}
          >
            Annulla
          </button>
        </div>
      </form>
    </section>
  )
}
