import { useRef, useState } from 'react'
import { toPng } from 'html-to-image'
import { fmt, type Resumen } from '../api'

export default function ShareCard({ r }: { r: Resumen }) {
  const ref = useRef<HTMLDivElement>(null)
  const [msg, setMsg] = useState('')

  async function render(): Promise<Blob | null> {
    if (!ref.current) return null
    const url = await toPng(ref.current, { pixelRatio: 2, cacheBust: true })
    return await (await fetch(url)).blob()
  }

  async function download() {
    const blob = await render()
    if (!blob) return
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `${r.nombre.toLowerCase()}-${r.anio}.png`
    a.click()
    URL.revokeObjectURL(a.href)
  }

  async function share() {
    try {
      const blob = await render()
      const file = blob ? new File([blob], `${r.nombre}-${r.anio}.png`, { type: 'image/png' }) : null
      const data: ShareData = { title: `${r.nombre}, ${r.anio}`, text: `Mi nombre en cifras: ${r.nombre}, ${r.anio}`, url: location.href }
      if (file && navigator.canShare?.({ files: [file] })) data.files = [file]
      if (navigator.share) await navigator.share(data)
      else {
        await navigator.clipboard.writeText(location.href)
        setMsg('Enlace copiado')
      }
    } catch {
      /* user cancelled */
    }
  }

  const stats = [
    [r.ranking ? `N° ${r.ranking}` : 'Sin registro', `entre ${r.n_nombres ? fmt(r.n_nombres) : '—'} nombres de ${r.anio}`],
    [fmt(r.vivos), 'personas vivas con tu nombre'],
    [`${r.share_f_pct}%`, 'de las inscripciones son de mujeres'],
    [r.alive_city ? fmt(r.alive_city) : 'Solo tú', `de tu edad en ${r.comuna_actual}, estimación`],
  ]

  return (
    <div className="share">
      <div className="sharecard" ref={ref}>
        <p className="sharecard__eyebrow">Nombres de Chile</p>
        <p className="sharecard__name">{r.nombre}</p>
        <p className="sharecard__year">{r.anio}</p>
        <dl className="sharecard__grid">
          {stats.map(([v, l]) => (
            <div key={l}>
              <dt>{v}</dt>
              <dd>{l}</dd>
            </div>
          ))}
        </dl>
        <p className="sharecard__foot">Registro Civil 1920-2021 · Censo 2024</p>
      </div>
      <div className="share__actions">
        <button className="btn" onClick={download}>
          Descargar imagen
        </button>
        <button className="btn btn--ghost" onClick={share}>
          Compartir
        </button>
        {msg && <span className="share__msg">{msg}</span>}
      </div>
    </div>
  )
}
