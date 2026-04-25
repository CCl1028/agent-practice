import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'

// Global styles (tokens, reset, layout, shared utilities)
import './styles/global.css'
// Component styles
import './styles/components/header.css'
import './styles/components/fund-card.css'
import './styles/components/sort-bar.css'
import './styles/components/bottom-input.css'
import './styles/components/drawer.css'
// Page styles
import './styles/pages/portfolio.css'
import './styles/pages/briefing.css'
import './styles/pages/diagnosis.css'
import './styles/pages/profile.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
)
