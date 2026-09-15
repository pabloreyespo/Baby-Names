import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api, ApiError, type StoryResponse } from '../api'
import { Reveal } from '../components/Reveal'
import ShareCard from '../components/ShareCard'
import Slide from '../components/Slide'

export default function Story() {
  const [params] = useSearchParams()
  const key = params.toString()
  const [res, setRes] = useState<{ key: string; data?: StoryResponse; err?: string }>({ key: '' })

  useEffect(() => {
    let live = true
    api
      .story(Object.fromEntries(params.entries()))
      .then((data) => live && setRes({ key, data }))
      .catch((e: unknown) => live && setRes({ key, err: e instanceof ApiError ? e.message : 'No pudimos armar tu historia' }))
    return () => {
      live = false
    }
  }, [params, key])

  const loaded = res.key === key
  const data = loaded ? res.data : undefined
  const err = loaded ? res.err : undefined

  if (err)
    return (
      <section className="notice">
        <p className="eyebrow">Algo no cuadra</p>
        <h2 className="hero__title">No pudimos armar esta historia</h2>
        <p className="lede">{err}</p>
        <Link className="btn" to="/">
          Volver
        </Link>
      </section>
    )
  if (!data) return <p className="notice lede">Preparando tu historia...</p>

  return (
    <article className="story">
      {data.slides.map((s) => (
        <Slide s={s} nombre={data.nombre} key={s.id} />
      ))}
      <Reveal as="section" className="chapter chapter--share">
        <p className="eyebrow">
          <span className="eyebrow__n">{String(data.slides.length + 1).padStart(2, '0')}</span>Para compartir
        </p>
        <h2 className="chapter__title">Tu nombre en una tarjeta</h2>
        <ShareCard r={data.resumen} />
        <p className="story__again">
          <Link to="/">Probar con otro nombre</Link>
        </p>
      </Reveal>
    </article>
  )
}
