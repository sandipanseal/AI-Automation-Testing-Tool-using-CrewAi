import React from 'react'
import { Link } from 'react-router-dom'

const Card = ({ to, title, desc }: { to: string; title: string; desc: string }) => (
  <Link to={to} className="glass neo hover-tilt rounded-2xl p-8 hover:no-underline group">
    <h2 className="text-xl font-semibold text-white mb-2">{title}</h2>
    <p className="text-sm text-white/70 group-hover:opacity-90">{desc}</p>
  </Link>
)

export default function Home() {
  return (
    <div className="grid gap-6 sm:grid-cols-2">
      <Card
        to="/new"
        title="Create New Test"
        desc="Provide Application URL, test name, and description. We’ll generate & run it."
      />
      <Card
        to="/tests"
        title="All Tests"
        desc="Browse all tests with status and Last Run details."
      />
    </div>
  )
}
