import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Shell from './layouts/Shell'
import Home from './pages/Home'
import NewTest from './pages/NewTest'
import RunView from './pages/RunView'
import Tests from './pages/Tests'
import TestDetail from './pages/TestDetail'
import ScenarioSelect from './pages/ScenarioSelect'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Shell />}>
          <Route path="/" element={<Home />} />
          <Route path="/new" element={<NewTest />} />
          <Route path="/runs/:runId" element={<RunView />} />
          <Route path="/tests" element={<Tests />} />
          <Route path="/tests/:name" element={<TestDetail />} />
          <Route path="*" element={<Navigate to="/" replace />} />
          <Route path="/tests/:name/select" element={<ScenarioSelect />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}