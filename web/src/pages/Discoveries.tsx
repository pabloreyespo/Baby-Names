import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type DiscoveryMeta } from '../api'
import { Reveal } from '../components/Reveal'

export default function Discoveries() {
  const [items, setItems] = useState<DiscoveryMeta[] | null>(null)
  useEffect(() => {
    api.discoveries().then(setItems).catch(() => setItems([]))
  }, [])
  return (
    <section className="index">
      <p className="eyebrow">Descubrimientos</p>
      <h1 className="hero__title">Lo que dicen los nombres</h1>
      <p className="lede">Análisis publicados a partir del registro de nombres. Cada uno es una pieza breve con sus gráficos, escrita desde los datos.</p>
      {items === null && <p className="lede">Cargando...</p>}
      <ul className="grid">
        {items?.map((d, i) => (
          <Reveal key={d.slug} className="grid__cell">
            <li>
              <Link to={`/descubrimientos/${d.slug}`} className="card card--link">
                <span className="card__n">{String(i + 1).padStart(2, '0')}</span>
                <span className="card__title">{d.title}</span>
                <span className="card__summary">{d.summary}</span>
                <span className="card__date">{d.date}</span>
              </Link>
            </li>
          </Reveal>
        ))}
      </ul>
    </section>
  )
}
