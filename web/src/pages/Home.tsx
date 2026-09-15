import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, fmt, type Comuna, type Family } from '../api'

const YEARS = Array.from({ length: 2021 - 1920 + 1 }, (_, i) => 2021 - i)

export default function Home() {
  const nav = useNavigate()
  const [comunas, setComunas] = useState<Comuna[]>([])
  const [nombre, setNombre] = useState('')
  const [sugs, setSugs] = useState<string[]>([])
  const [fam, setFam] = useState<Family | null>(null)
  const [anio, setAnio] = useState(1995)
  const [nac, setNac] = useState('')
  const [act, setAct] = useState('')
  const [err, setErr] = useState('')

  const shuffle = () => api.randomName().then((r) => setNombre(r.nombre)).catch(() => {})

  useEffect(() => {
    api.comunas().then(setComunas).catch(() => setErr('No pudimos cargar las comunas, revisa que la API esté arriba'))
    api.randomName().then((r) => setNombre((n) => n || r.nombre)).catch(() => {})
  }, [])

  useEffect(() => {
    const q = nombre.trim()
    const t = setTimeout(() => {
      if (q.length < 2) {
        setSugs([])
        setFam(null)
        return
      }
      api.suggest(q).then(setSugs).catch(() => {})
      api
        .family(q)
        .then(setFam)
        .catch(() => setFam(null))
    }, 250)
    return () => clearTimeout(t)
  }, [nombre])

  const names = new Set(comunas.map((c) => c.comuna))
  const valid = nombre.trim().length >= 2 && names.has(nac) && names.has(act)

  function submit(e: React.FormEvent) {
    e.preventDefault()
    if (!valid) return setErr('Completa el nombre y elige comunas de la lista')
    nav(`/historia?${new URLSearchParams({ nombre: nombre.trim(), anio: String(anio), comuna_nac: nac, comuna_actual: act })}`)
  }

  return (
    <section className="hero">
      <p className="eyebrow">Tu nombre en cifras</p>
      <h1 className="hero__title">¿Cuántas personas se llaman como tú?</h1>
      <p className="lede">
        Un siglo de inscripciones del Registro Civil y el Censo 2024, contados para una sola persona: tú. Escribe tu nombre, tu año y tus comunas.
      </p>

      <form className="form card" onSubmit={submit} noValidate>
        <label className="field field--name">
          <span>
            Primer nombre
            <button type="button" className="linkbtn" onClick={shuffle}>
              otro al azar
            </button>
          </span>
          <input list="sugs" value={nombre} onChange={(e) => setNombre(e.target.value)} maxLength={40} autoComplete="given-name" placeholder="Martina" required />
          <datalist id="sugs">
            {sugs.map((s) => (
              <option key={s} value={s} />
            ))}
          </datalist>
          {fam && fam.formas.length > 1 && (
            <span className="field__hint">
              También se escribe {fam.formas.filter((f) => f.nombre !== fam.nombre).slice(0, 6).map((f) => f.nombre).join(', ')}
              {fam.formas.length > 7 ? ` y ${fmt(fam.formas.length - 7)} formas más` : ''}. Las verás todas en tu historia.
            </span>
          )}
        </label>

        <div className="form__row">
          <label className="field">
            <span>Año de nacimiento</span>
            <select value={anio} onChange={(e) => setAnio(Number(e.target.value))}>
              {YEARS.map((y) => (
                <option key={y}>{y}</option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Comuna donde naciste</span>
            <input list="comunas" value={nac} onChange={(e) => setNac(e.target.value)} placeholder="Concepción" required />
          </label>
          <label className="field">
            <span>Comuna donde vives</span>
            <input list="comunas" value={act} onChange={(e) => setAct(e.target.value)} placeholder="Santiago" required />
          </label>
        </div>
        <datalist id="comunas">
          {comunas.map((c) => (
            <option key={c.cut} value={c.comuna}>
              {c.region}
            </option>
          ))}
        </datalist>

        <div className="form__actions">
          <button type="submit" className="btn btn--big" disabled={!valid}>
            Ver mi historia
          </button>
          {err && <p className="form__error">{err}</p>}
        </div>
      </form>
    </section>
  )
}
