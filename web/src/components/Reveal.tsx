import { useEffect, useRef, useState, type ReactNode } from 'react'

/** Adds the "is-in" class once the element enters the viewport. CSS does the fade and rise. */
export function Reveal({ children, className = '', as: Tag = 'div' }: { children: ReactNode; className?: string; as?: 'div' | 'section' }) {
  const ref = useRef<HTMLDivElement>(null)
  const [seen, setSeen] = useState(false)
  useEffect(() => {
    const el = ref.current
    if (!el || seen) return
    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) setSeen(true)
      },
      { threshold: 0.2 },
    )
    io.observe(el)
    return () => io.disconnect()
  }, [seen])
  return (
    <Tag ref={ref} className={`reveal ${seen ? 'is-in' : ''} ${className}`}>
      {children}
    </Tag>
  )
}

const REDUCED = typeof matchMedia !== 'undefined' && matchMedia('(prefers-reduced-motion: reduce)').matches

/** Counts the first number inside `text` up from zero when the element becomes visible. Prefix and suffix are kept. */
export function CountUp({ text, duration = 1400 }: { text: string; duration?: number }) {
  const ref = useRef<HTMLSpanElement>(null)
  const [shown, setShown] = useState(REDUCED ? text : '')
  const m = text.match(/(\d[\d.]*)/)
  useEffect(() => {
    if (REDUCED || !m) return setShown(text)
    const el = ref.current
    if (!el) return
    const target = Number(m[1].replace(/\./g, ''))
    const [pre, post] = [text.slice(0, m.index), text.slice((m.index ?? 0) + m[1].length)]
    let raf = 0
    const io = new IntersectionObserver(
      (entries) => {
        if (!entries.some((e) => e.isIntersecting)) return
        io.disconnect()
        const t0 = performance.now()
        const tick = (now: number) => {
          const p = Math.min(1, (now - t0) / duration)
          const eased = 1 - Math.pow(1 - p, 3)
          setShown(pre + new Intl.NumberFormat('es-CL').format(Math.round(target * eased)) + post)
          if (p < 1) raf = requestAnimationFrame(tick)
        }
        raf = requestAnimationFrame(tick)
      },
      { threshold: 0.5 },
    )
    io.observe(el)
    return () => {
      io.disconnect()
      cancelAnimationFrame(raf)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [text])
  return <span ref={ref}>{shown || (m ? text.replace(m[1], '0') : text)}</span>
}
