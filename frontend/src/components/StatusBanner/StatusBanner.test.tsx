import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { StatusBanner } from './StatusBanner'

describe('StatusBanner', () => {
  it('shows the message in an alert with the info tone by default', () => {
    render(<StatusBanner message="Everything is fine" />)

    const alert = screen.getByRole('alert')
    expect(alert).toHaveTextContent('Everything is fine')
    expect(alert).toHaveClass('MuiAlert-colorInfo')
  })

  it('shows the message in an alert with the error tone', () => {
    render(<StatusBanner tone="error" message="Could not load the conversation" />)

    const alert = screen.getByRole('alert')
    expect(alert).toHaveTextContent('Could not load the conversation')
    expect(alert).toHaveClass('MuiAlert-colorError')
  })
})
