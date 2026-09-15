export type Slide = {
  id: string
  kicker: string
  title: string
  body: string[]
  big?: string
  big_label?: string
  chart?: Record<string, unknown>
  charts?: SmallChart[]
  formas?: Forma[]
  cover?: boolean
  closing?: boolean
  page: number
  pages: number
}

export type SmallChart = { title: string; spec: Record<string, unknown> }
export type Items = { title: string; rows: { label: string; value: string }[] }
export type Forma = { nombre: string; inscritos: number; exacto: boolean }
export type Family = { nombre: string; total: number; formas: Forma[] }

export type Resumen = {
  nombre: string
  anio: number
  ranking: number | null
  n_nombres: number | null
  vivos: number
  share_f_pct: number
  alive_city: number
  comuna_actual: string
  born_city: number
  comuna_nac: string
}

export type StoryResponse = { nombre: string; anio: number; slides: Slide[]; resumen: Resumen }
export type Comuna = { cut: number; comuna: string; region: string; poblacion: number }
export type DiscoveryMeta = { slug: string; title: string; date: string; summary: string }
export type Section = { heading: string | null; body: string[]; chart: Record<string, unknown> | null; charts?: SmallChart[]; items?: Items }
export type DiscoveryFull = DiscoveryMeta & { sections: Section[] }

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function get<T>(path: string, params?: Record<string, string>): Promise<T> {
  const qs = params ? '?' + new URLSearchParams(params).toString() : ''
  const r = await fetch(`/api${path}${qs}`)
  if (!r.ok) {
    let detail = 'Algo salió mal'
    try {
      const j = await r.json()
      detail = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail)
    } catch {
      /* ignore */
    }
    throw new ApiError(r.status, detail)
  }
  return r.json()
}

export const api = {
  comunas: () => get<Comuna[]>('/comunas'),
  suggest: (q: string) => get<string[]>('/names/suggest', { q }),
  randomName: () => get<{ nombre: string }>('/names/random'),
  family: (nombre: string) => get<Family>('/names/family', { nombre }),
  story: (p: Record<string, string>) => get<StoryResponse>('/story', p),
  discoveries: () => get<DiscoveryMeta[]>('/discoveries'),
  discovery: (slug: string) => get<DiscoveryFull>(`/discoveries/${encodeURIComponent(slug)}`),
}

export const fmt = (n: number) => new Intl.NumberFormat('es-CL').format(n)
