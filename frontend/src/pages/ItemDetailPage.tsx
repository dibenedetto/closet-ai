import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { deleteItem, getItem, itemImageUrl, type Item } from '../api/items'

export default function ItemDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [item, setItem] = useState<Item | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [deleting, setDeleting] = useState(false)

  const itemId = Number(id)
  const isValidId = Number.isInteger(itemId) && itemId > 0

  useEffect(() => {
    if (!isValidId) {
      setError('ID non valido')
      return
    }
    getItem(itemId)
      .then(setItem)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)))
  }, [itemId, isValidId])

  async function onDelete() {
    if (!item || deleting) return
    if (!confirm(`Eliminare "${item.name}" (#${item.id})?`)) return
    setDeleting(true)
    try {
      await deleteItem(item.id)
      navigate('/')
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
      setDeleting(false)
    }
  }

  if (error) {
    return (
      <p className="error">
        Errore: {error} — <Link to="/">torna al guardaroba</Link>
      </p>
    )
  }
  if (item == null) return <p className="muted">Caricamento…</p>

  return (
    <section className="detail">
      <div>
        {item.image_path ? (
          <img src={itemImageUrl(item.id)} alt={item.name} />
        ) : (
          <div className="panel muted">Nessuna immagine</div>
        )}
      </div>
      <div>
        <h2 style={{ marginTop: 0 }}>{item.name}</h2>
        <div className="meta">
          <div className="kv"><span className="muted">ID</span><b>#{item.id}</b></div>
          <div className="kv"><span className="muted">Categoria</span><b>{item.category ?? '—'}</b></div>
          <div className="kv"><span className="muted">Colore</span><b>{item.color ?? '—'}</b></div>
          <div className="kv">
            <span className="muted">Prezzo</span>
            <b>{item.price != null ? `€ ${item.price.toFixed(2)}` : '—'}</b>
          </div>
          <div className="kv">
            <span className="muted">Data acquisto</span>
            <b>{item.purchase_date ?? '—'}</b>
          </div>
          <div className="kv">
            <span className="muted">Creato</span>
            <b>{new Date(item.created_at).toLocaleString('it-IT')}</b>
          </div>
        </div>
        <div className="actions">
          <button className="danger" onClick={onDelete} disabled={deleting}>
            {deleting ? 'Elimino…' : 'Elimina'}
          </button>
          <button type="button" className="ghost" onClick={() => navigate('/')} disabled={deleting}>
            Indietro
          </button>
        </div>
      </div>
    </section>
  )
}
