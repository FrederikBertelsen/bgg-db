import { Navigate, Route, Routes } from 'react-router-dom'
import { GamePage } from './pages/GamePage'
import { SearchPage } from './pages/SearchPage'
import './App.css'

function App() {
  return (
    <Routes>
      <Route path="/" element={<SearchPage />} />
      <Route path="/game/:id" element={<GamePage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
