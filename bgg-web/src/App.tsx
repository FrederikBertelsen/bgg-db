import { Navigate, Route, Routes } from 'react-router-dom'
import { SiteHeader } from './components/SiteHeader'
import { HomePage } from './pages/HomePage'
import { GamePage } from './pages/GamePage'
import { SearchPage } from './pages/SearchPage'
import './App.css'

function App() {
  return (
    <div className="appShell">
      <SiteHeader />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/search" element={<SearchPage />} />
        <Route path="/game/:id" element={<GamePage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  )
}

export default App
