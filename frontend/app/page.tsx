"use client"

import { useEffect, useState } from "react"

export default function Home() {
  const [status, setStatus] = useState<string>("Loading...")

  useEffect(() => {
    fetch("http://localhost:8000/")
      .then(res => res.json())
      .then(data => setStatus(data.status))
      .catch(err => setStatus("Error: " + err.message))
  }, [])

  return (
    <main className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-3xl font-bold mb-4">Full-Stack Test</h1>
        <p className="text-xl">{status}</p>
      </div>
    </main>
  )
}