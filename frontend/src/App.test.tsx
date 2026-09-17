import '@testing-library/jest-dom/vitest'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { App } from './App'

describe('App', () => {
  it('states the paper-only safety boundary', () => {
    render(<App />)
    expect(screen.getByText(/No real orders are supported/i)).toBeInTheDocument()
  })
})
