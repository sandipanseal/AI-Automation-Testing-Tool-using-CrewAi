import React from 'react'
import { NavLink } from 'react-router-dom'

export default function Sidebar() {
  const base = 'block px-4 py-2 rounded-lg transition'
  const idle = 'text-white/80 hover:text-white hover:bg-white/10'
  const active = 'bg-white/10 text-white'
  return (
    <aside className="hidden md:block w-60 sticky top-0 self-start h-[calc(100vh-64px)] p-4">
      <div className="glass neo-sm rounded-2xl p-4 space-y-1">
        <NavLink to="/" className={({isActive}) => `${base} ${isActive ? active : idle}`}>Home</NavLink>
        <NavLink to="/new" className={({isActive}) => `${base} ${isActive ? active : idle}`}>Create New Test</NavLink>
        <NavLink to="/tests" className={({isActive}) => `${base} ${isActive ? active : idle}`}>All Tests</NavLink>
      </div>
    </aside>
  )
}
