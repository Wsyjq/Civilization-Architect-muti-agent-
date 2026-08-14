import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { GameProvider } from './stores/GameContext'
import StartPage from './pages/StartPage'

const SelectPage = lazy(() => import('./pages/SelectPage'))
const EditorPage = lazy(() => import('./pages/EditorPage'))
const ResultPage = lazy(() => import('./pages/ResultPage'))

function App() {
  return (
    <GameProvider>
      <BrowserRouter>
        <div className="min-h-screen bg-cyber-gradient">
          {/* 背景粒子效果 */}
          <div className="fixed inset-0 pointer-events-none overflow-hidden">
            <div className="absolute w-full h-full bg-cyber-glow opacity-30" />
          </div>

          {/* 主内容 */}
          <div className="relative z-10">
            <Suspense fallback={<div className="flex items-center justify-center min-h-screen text-cyber-text-muted">加载中...</div>}>
              <Routes>
                <Route path="/" element={<StartPage />} />
                <Route path="/select" element={<SelectPage />} />
                <Route path="/editor/:gameId" element={<EditorPage />} />
                <Route path="/result/:gameId" element={<ResultPage />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </Suspense>
          </div>
        </div>
      </BrowserRouter>
    </GameProvider>
  )
}

export default App