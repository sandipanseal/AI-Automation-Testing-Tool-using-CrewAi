import React, { useState } from 'react'
import Form from '../components/Form'
import { startRun } from '../lib/api'
import { useNavigate } from 'react-router-dom'

export default function NewTest() {
  const [isRunning, setRunning] = useState(false)
  const navigate = useNavigate()

  return (
    <Form
      isRunning={isRunning}
      onSubmit={async (payload) => {
        setRunning(true)
        try {
          const params = new URLSearchParams({
            url: payload.application_url,
            desc: payload.test_description
          })
          navigate(`/tests/${encodeURIComponent(payload.test_name)}/select?${params.toString()}`)
        } finally {
          setRunning(false)
        }
      }}
    />
  )
}
