import { screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { renderWithTheme } from '../../../testUtils'
import { monoFont } from '../../../utils/theme'
import { sampleMessages } from '../fixtures'
import { UNKNOWN_ENTITLEMENT_LABEL, UNKNOWN_HUMAN_REASON_LABEL } from '../labels'
import type { DisruptionDecision } from '../types'
import { DecisionCard } from './DecisionCard'

function sample(id: string): DisruptionDecision {
  const decision = sampleMessages.find((message) => message.id === id)?.decision
  if (!decision) {
    throw new Error(`fixture ${id} has no decision`)
  }
  return structuredClone(decision)
}

const abc123 = () => sample('sample-2')

function renderCard(decision: DisruptionDecision, mode: 'light' | 'dark' = 'light') {
  return renderWithTheme(<DecisionCard decision={decision} />, mode)
}

describe('DecisionCard sections', () => {
  it('is a region named by its title', () => {
    renderCard(abc123())

    expect(screen.getByRole('region', { name: 'Your trip update' })).toBeInTheDocument()
  })

  it('shows the four sections in order for a full decision', () => {
    renderCard(abc123())

    const headings = screen.getAllByRole('heading', { level: 3 }).map((heading) => heading.textContent)
    expect(headings).toEqual(['What happened', 'Your benefits', 'Proposed option', 'Next step'])
  })

  it('omits the proposed option section when there is no recommended option', () => {
    const decision = abc123()
    decision.decision.recommended_option = null
    renderCard(decision)

    expect(screen.queryByText('Proposed option')).not.toBeInTheDocument()
  })

  it('omits the benefits section when there are no entitlements', () => {
    const decision = sample('sample-6')
    renderCard(decision)

    expect(screen.queryByText('Your benefits')).not.toBeInTheDocument()
  })

  it('omits the next step when no human is required', () => {
    renderCard(sample('sample-5'))

    expect(screen.queryByText('Next step')).not.toBeInTheDocument()
    expect(screen.queryByText(/An agent will review and confirm/)).not.toBeInTheDocument()
  })
})

describe('DecisionCard flights', () => {
  it('shows a delayed flight with route, status, delay and new departure', () => {
    renderCard(abc123())

    const row = screen.getByText('NB500').closest('li') as HTMLElement
    expect(within(row).getByText('SCL → LIM')).toBeInTheDocument()
    expect(within(row).getByText('Delayed')).toBeInTheDocument()
    expect(within(row).getByText('160 min')).toBeInTheDocument()
    expect(within(row).getByText('New departure 17:10')).toBeInTheDocument()
  })

  it('shows the status as text, not only as a color', () => {
    renderCard(abc123(), 'dark')

    expect(screen.getByText('Delayed')).toBeVisible()
    expect(screen.getByText('On schedule')).toBeVisible()
  })

  it('shows a cancelled flight without delay figures', () => {
    renderCard(sample('sample-5'))

    const row = screen.getByText('NB301').closest('li') as HTMLElement
    expect(within(row).getByText('Cancelled')).toBeInTheDocument()
    expect(within(row).queryByText(/min$/)).not.toBeInTheDocument()
  })

  it.each(['UNVERIFIED', 'CONFLICTING'])('shows %s as "Being confirmed" with no delay or time', (status) => {
    const decision = abc123()
    decision.assessment.segments[0].status = status
    renderCard(decision)

    const row = screen.getByText('NB500').closest('li') as HTMLElement
    expect(within(row).getByText('Being confirmed')).toBeInTheDocument()
    expect(within(row).queryByText('160 min')).not.toBeInTheDocument()
    expect(within(row).queryByText(/New departure/)).not.toBeInTheDocument()
    expect(within(row).queryByText(/\d{2}:\d{2}/)).not.toBeInTheDocument()
  })

  it('shows a notice that the missed connection will be missed', () => {
    renderCard(abc123())

    expect(screen.getByRole('note')).toHaveTextContent('Connection NB2410 (LIM → MEX) will be missed.')
  })

  it('shows no notice when no connection is missed', () => {
    renderCard(sample('sample-4'))

    expect(screen.queryByRole('note')).not.toBeInTheDocument()
  })
})

describe('DecisionCard benefits', () => {
  it('lists known entitlements in plain words', () => {
    renderCard(abc123())

    expect(screen.getByText('Free rebooking')).toBeInTheDocument()
    expect(screen.getByText('Priority handling')).toBeInTheDocument()
  })

  it('lists a repeated entitlement once', () => {
    const decision = abc123()
    decision.decision.applied_rules = [
      { entitlement: 'REBOOK_NO_FEE' },
      { entitlement: 'REBOOK_NO_FEE' },
      { entitlement: 'MEAL_VOUCHER' },
    ]
    renderCard(decision)

    expect(screen.getAllByText('Free rebooking')).toHaveLength(1)
    expect(screen.getByText('Meal voucher')).toBeInTheDocument()
  })

  it('shows generic text for an unknown entitlement, never the code', () => {
    const decision = abc123()
    decision.decision.applied_rules = [{ entitlement: 'UPGRADE_LOUNGE' }]
    const { container } = renderCard(decision)

    expect(screen.getByText(UNKNOWN_ENTITLEMENT_LABEL)).toBeInTheDocument()
    expect(container).not.toHaveTextContent('UPGRADE_LOUNGE')
  })

  it('neither promises nor quantifies compensation', () => {
    const { container } = renderCard(sample('sample-4'))

    expect(screen.getByText('Compensation request: an agent will review it')).toBeInTheDocument()
    expect(container.textContent).not.toMatch(/\d+\s?(CLP|USD|EUR)|\$\s?\d|approved|denied|granted/i)
  })
})

describe('DecisionCard proposed option', () => {
  it('shows flight, route, date, time and no extra cost', () => {
    renderCard(abc123())

    const section = screen.getByText('Proposed option').parentElement as HTMLElement
    expect(within(section).getByText('NB2412')).toBeInTheDocument()
    expect(within(section).getByText('LIM → MEX')).toBeInTheDocument()
    expect(within(section).getByText('16 Sep 2026 · 08:15')).toBeInTheDocument()
    expect(within(section).getByText('No extra cost')).toBeInTheDocument()
  })

  it('does not say the booking was changed', () => {
    const { container } = renderCard(abc123())

    expect(container.textContent).not.toMatch(/(booking|reservation).{0,20}(changed|updated|modified)|has been changed/i)
  })

  it('omits the no-extra-cost chip when the fare difference is not zero', () => {
    const decision = abc123()
    decision.decision.recommended_option!.fare_difference = 50000
    renderCard(decision)

    expect(screen.queryByText('No extra cost')).not.toBeInTheDocument()
  })
})

describe('DecisionCard next step', () => {
  it('says an agent will confirm before any change, with the reason in plain words', () => {
    renderCard(abc123())

    expect(screen.getByText('An agent will review and confirm before any change is made.')).toBeInTheDocument()
    expect(screen.getByText('Priority handling for travellers with a minor')).toBeInTheDocument()
  })

  it('shows a generic reason when a reason has no label, never the code', () => {
    const decision = abc123()
    decision.decision.human_reasons = ['R9_SECRET_RULE']
    const { container } = renderCard(decision)

    expect(screen.getByText(UNKNOWN_HUMAN_REASON_LABEL)).toBeInTheDocument()
    expect(container).not.toHaveTextContent('R9_SECRET_RULE')
  })

  it('shows both reasons when compensation is requested', () => {
    renderCard(sample('sample-4'))

    expect(screen.getByText("Your compensation request needs an agent's review")).toBeInTheDocument()
    expect(screen.getByText('Priority handling for travellers with a minor')).toBeInTheDocument()
  })
})

describe('DecisionCard references', () => {
  it('shows the policy and case references in monospace', () => {
    renderCard(abc123())

    const policy = screen.getByText('POL-DELAY-2026-03')
    const caseId = screen.getByText('HC-90412')
    expect(screen.getByText(/Policy reference/)).toBeInTheDocument()
    expect(screen.getByText(/Case reference/)).toBeInTheDocument()
    expect(policy).toHaveStyle({ fontFamily: monoFont })
    expect(caseId).toHaveStyle({ fontFamily: monoFont })
  })

  it('omits a reference that is missing', () => {
    renderCard(sample('sample-6'))

    expect(screen.queryByText(/Policy reference/)).not.toBeInTheDocument()
    expect(screen.getByText(/Case reference/)).toBeInTheDocument()
  })
})

describe('DecisionCard internal data', () => {
  it.each(['sample-2', 'sample-4', 'sample-5', 'sample-6'])('shows no internal data for fixture %s', (id) => {
    const { container } = renderCard(sample(id))
    const text = container.textContent ?? ''

    for (const forbidden of ['LEGACY_MIRROR', 'OPS_CORE', 'AIRPORT_FEED', '12.345.678-9']) {
      expect(text).not.toContain(forbidden)
    }
    expect(text).not.toMatch(/\bR[1-5]\b/)
    expect(text).not.toMatch(/\b[A-Z]{2,}_[A-Z_]+\b/)
  })
})
