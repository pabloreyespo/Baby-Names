import type { Slide as SlideT } from '../api'
import Chart from './Chart'
import { ChartGrid } from './Extras'
import Formas from './Formas'
import { CountUp, Reveal } from './Reveal'

export default function Slide({ s, nombre }: { s: SlideT; nombre: string }) {
  return (
    <Reveal as="section" className={`chapter ${s.cover ? 'chapter--cover' : ''} ${s.closing ? 'chapter--closing' : ''}`}>
      <p className="eyebrow">
        <span className="eyebrow__n">{String(s.page).padStart(2, '0')}</span>
        {s.kicker}
      </p>
      <h2 className="chapter__title">{s.title}</h2>
      <div className={`chapter__grid ${s.chart ? 'chapter__grid--chart' : ''}`}>
        <div className="chapter__text">
          {s.big && (
            <p className="big">
              <span className="big__value">
                <CountUp text={s.big} />
              </span>
              <span className="big__label">{s.big_label}</span>
            </p>
          )}
          {s.body.map((p, i) => (
            <p key={i} className="chapter__p">
              {p}
            </p>
          ))}
        </div>
        {s.chart && (
          <div className="chapter__chart card">
            <Chart spec={s.chart} />
          </div>
        )}
      </div>
      {s.charts && <ChartGrid charts={s.charts} />}
      {s.formas && <Formas formas={s.formas} highlight={nombre} />}
    </Reveal>
  )
}
