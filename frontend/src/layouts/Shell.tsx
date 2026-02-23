import React from 'react'
import Header from '../components/Header'
import Sidebar from '../components/Sidebar'
import { Outlet, useLocation } from 'react-router-dom'

export default function Shell() {
  const { pathname } = useLocation()
  const isHome = pathname === '/'
  return (
    <div className="min-h-screen relative aurora">
      <Header />
      {isHome ? (
        <div className="relative z-10 mx-auto max-w-6xl px-4 py-10">
          <main className="space-y-6">
            <Outlet />
          </main>
        </div>
      ) : (
        <div className="relative z-10 mx-auto max-w-6xl px-4 py-6 grid grid-cols-1 md:grid-cols-[240px_1fr] gap-6">
          <Sidebar />
          <main className="space-y-6">
            <Outlet />
          </main>
        </div>
      )}
    </div>
  )
}
