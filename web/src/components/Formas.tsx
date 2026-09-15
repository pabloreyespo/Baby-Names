import { useState } from 'react'
import { fmt, type Forma } from '../api'

const FIRST = 8

/** Every spelling of a name, as chips. Exact-sound spellings are solid; one-letter typos are outlined. */
export default function Formas({ formas, highlight }: { formas: Forma[]; highlight: string }) {
  const [all, setAll] = useState(false)
  const shown = all ? formas : formas.slice(0, FIRST)
  return (
    <div className="formas">
      <ul className="formas__list">
        {shown.map((f) => (
          <li key={f.nombre} className={`chip ${f.exacto ? '' : 'chip--typo'} ${f.nombre === highlight ? 'chip--me' : ''}`} title={f.exacto ? 'Suena igual' : 'Falta de una letra'}>
            <span>{f.nombre}</span>
            <span className="chip__n">{fmt(f.inscritos)}</span>
          </li>
        ))}
      </ul>
      {formas.length > FIRST && (
        <button type="button" className="linkbtn" onClick={() => setAll((v) => !v)}>
          {all ? 'Ver menos' : `Otras ${fmt(formas.length - FIRST)} formas`}
        </button>
      )}
      <p className="formas__legend">Rellenas: suenan igual. Con borde: falta de una letra.</p>
    </div>
  )
}
