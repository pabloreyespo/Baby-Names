import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, type DiscoveryFull } from '../api'
import Chart from '../components/Chart'
import { ChartGrid, ItemList } from '../components/Extras'
import { Reveal } from '../components/Reveal'

export default function Discovery() {
  const { slug = '' } = useParams()
  const [d, setD] = useState<DiscoveryFull | null>(null)
  const [err, setErr] = useState('')
  useEffect(() => {
    api.discovery(slug).then(setD).catch(() => setErr('No encontramos este descubrimiento'))
  }, [slug])

  if (err)
    return (
      <section className="notice">
        <p className="lede">{err}</p>
        <Link className="btn" to="/descubrimientos">
          Volver
        </Link>
      </section>
    )
  if (!d) return <p className="notice lede">Cargando...</p>

  return (
    <article className="essay">
      <p className="eyebrow">Descubrimiento · {d.date}</p>
      <h1 className="hero__title">{d.title}</h1>
      <p className="lede">{d.summary}</p>
      {d.sections.map((s, i) => (
        <Reveal as="section" key={i} className="essay__section">
          {s.heading && <h2 className="essay__heading">{s.heading}</h2>}
          {s.body.map((p, k) => (
            <p key={k} className="chapter__p">
              {p}
            </p>
          ))}
          {s.chart && (
            <div className="card">
              <Chart spec={s.chart} />
            </div>
          )}
          {s.charts && <ChartGrid charts={s.charts} />}
          {s.items && <ItemList items={s.items} />}
        </Reveal>
      ))}
      <p className="story__again">
        <Link to="/descubrimientos">Volver a descubrimientos</Link>
      </p>
    </article>
  )
}
