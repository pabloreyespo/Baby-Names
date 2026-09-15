import { Link, NavLink, Outlet } from 'react-router-dom'

export default function App() {
  return (
    <>
      <header className="nav">
        <Link to="/" className="nav__brand">
          Nombres de Chile
        </Link>
        <nav className="nav__links" aria-label="Secciones">
          <NavLink to="/" end>
            Tu nombre
          </NavLink>
          <NavLink to="/descubrimientos">Descubrimientos</NavLink>
        </nav>
      </header>
      <main className="page">
        <Outlet />
      </main>
      <footer className="foot">
        <span>Registro Civil 1920-2021 · Censo 2024, INE</span>
        <span>Las cifras por comuna son estimaciones.</span>
      </footer>
    </>
  )
}
