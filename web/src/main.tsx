import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import './index.css'
import App from './App.tsx'
import Home from './pages/Home.tsx'
import Story from './pages/Story.tsx'
import Discoveries from './pages/Discoveries.tsx'
import Discovery from './pages/Discovery.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route element={<App />}>
          <Route index element={<Home />} />
          <Route path="historia" element={<Story />} />
          <Route path="descubrimientos" element={<Discoveries />} />
          <Route path="descubrimientos/:slug" element={<Discovery />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </StrictMode>,
)
