import { type Items, type SmallChart } from '../api'
import Chart from './Chart'

/** Grid of small titled charts (top tens by sex, word clouds per family). */
export function ChartGrid({ charts }: { charts: SmallChart[] }) {
  return (
    <div className="chartgrid">
      {charts.map((c) => (
        <figure key={c.title} className="card chartgrid__item">
          <figcaption className="chartgrid__title">{c.title}</figcaption>
          <Chart spec={c.spec} />
        </figure>
      ))}
    </div>
  )
}

/** Long lists live behind a native disclosure so the prose stays short. */
export function ItemList({ items }: { items: Items }) {
  return (
    <details className="items">
      <summary className="items__summary">{items.title}</summary>
      <dl className="items__list">
        {items.rows.map((r) => (
          <div key={r.label} className="items__row">
            <dt>{r.label}</dt>
            <dd>{r.value}</dd>
          </div>
        ))}
      </dl>
    </details>
  )
}
