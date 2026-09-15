import { VegaEmbed } from 'react-vega'
import type { VisualizationSpec } from 'vega-embed'

const options = { actions: false, renderer: 'svg' as const }

export default function Chart({ spec }: { spec: Record<string, unknown> }) {
  return (
    <figure className="chart">
      <VegaEmbed spec={spec as VisualizationSpec} options={options} style={{ width: '100%' }} />
    </figure>
  )
}
