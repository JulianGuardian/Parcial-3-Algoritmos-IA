import { Box, Button, Chip, Paper, Typography, useTheme } from '@mui/material'
import { useId } from 'react'
import type { ReactNode } from 'react'

import { formatClock, formatDate } from '../../../utils/time'
import { appPalette, monoFont } from '../../../utils/theme'
import { entitlementLabel, humanReasonLabel, isVerifiedStatus, nextStepText, statusKind, statusLabel } from '../labels'
import type { DisruptionDecision, RecommendedOption, SegmentSummary } from '../types'

interface DecisionCardProps {
  decision: DisruptionDecision
  /** Shown only when the next step is CONFIRM_OPTION; sends the structured confirmation. */
  onConfirm?: (option: RecommendedOption) => void
  confirmDisabled?: boolean
}

const sectionTitleSx = {
  fontWeight: 800,
  color: 'text.secondary',
  display: 'block',
  mb: 1,
  textTransform: 'uppercase',
  letterSpacing: '0.04em',
} as const

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Box sx={{ mt: 2.5 }}>
      <Typography component="h3" variant="caption" sx={sectionTitleSx}>
        {title}
      </Typography>
      {children}
    </Box>
  )
}

function unique(values: string[]) {
  return [...new Set(values)]
}

function route(origin: string | null, destination: string | null) {
  return origin && destination ? `${origin} → ${destination}` : null
}

function StatusChip({ status }: { status: string }) {
  const theme = useTheme()
  const colors = appPalette[theme.palette.mode].status[statusKind(status)]

  return (
    <Chip
      size="small"
      label={statusLabel(status)}
      sx={{ bgcolor: colors.background, color: colors.foreground, border: `1px solid ${colors.foreground}` }}
    />
  )
}

function SegmentRow({ segment }: { segment: SegmentSummary }) {
  const verified = isVerifiedStatus(segment.status)
  const showDelay = verified && segment.status === 'DELAYED' && segment.delay_minutes > 0
  const departure = verified ? formatClock(segment.estimated_departure) : null

  return (
    <Box component="li" sx={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 1, py: 0.5 }}>
      <Typography component="span" sx={{ fontWeight: 700 }}>
        {segment.flight_number}
      </Typography>
      <Typography component="span" color="text.secondary">
        {route(segment.origin, segment.destination)}
      </Typography>
      <StatusChip status={segment.status} />
      {showDelay ? (
        <Typography component="span" variant="body2">
          {segment.delay_minutes} min
        </Typography>
      ) : null}
      {showDelay && departure ? (
        <Typography component="span" variant="body2" color="text.secondary">
          New departure {departure}
        </Typography>
      ) : null}
    </Box>
  )
}

function OptionSummary({ option }: { option: RecommendedOption }) {
  const when = [formatDate(option.date), option.departure].filter(Boolean).join(' · ')

  return (
    <Box sx={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 1 }}>
      <Typography component="span" sx={{ fontWeight: 700 }}>
        {option.flight_number}
      </Typography>
      <Typography component="span" color="text.secondary">
        {route(option.origin, option.destination)}
      </Typography>
      {when ? (
        <Typography component="span" variant="body2">
          {when}
        </Typography>
      ) : null}
      {option.fare_difference === 0 ? <Chip size="small" color="success" variant="outlined" label="No extra cost" /> : null}
    </Box>
  )
}

function Reference({ label, value }: { label: string; value: string }) {
  return (
    <Typography variant="caption" color="text.secondary" component="p" sx={{ m: 0 }}>
      {label}{' '}
      <Box component="span" sx={{ fontFamily: monoFont, color: 'text.primary' }}>
        {value}
      </Box>
    </Typography>
  )
}

export function DecisionCard({ decision, onConfirm, confirmDisabled = false }: DecisionCardProps) {
  const titleId = useId()
  const segments = decision.assessment.segments
  const benefits = unique(decision.decision.applied_rules.map((rule) => entitlementLabel(rule.entitlement)))
  const option = decision.decision.recommended_option
  const reasons = unique(decision.decision.human_reasons.map(humanReasonLabel))
  const policyRef = decision.decision.policy_ref
  const caseId = decision.actions.human_case?.case_id
  const missed = segments.filter((segment) => segment.missed_connection)
  const nextStep = decision.next_step ?? null
  const canConfirm = nextStep === 'CONFIRM_OPTION' && !decision.decision.requires_human && Boolean(option?.option_id) && Boolean(onConfirm)
  const otherStepText = !decision.decision.requires_human && nextStep && nextStep !== 'CONFIRM_OPTION' ? nextStepText(nextStep) : null

  return (
    <Paper component="section" aria-labelledby={titleId} sx={{ p: 3, width: '100%', bgcolor: 'background.paper' }}>
      <Typography id={titleId} component="h2" variant="subtitle1" sx={{ color: 'primary.main' }}>
        Your trip update
      </Typography>

      {segments.length > 0 ? (
        <Section title="What happened">
          <Box component="ul" sx={{ m: 0, p: 0, listStyle: 'none' }}>
            {segments.map((segment) => (
              <SegmentRow key={segment.segment_id} segment={segment} />
            ))}
          </Box>
          {missed.map((segment) => (
            <Typography
              key={segment.segment_id}
              role="note"
              sx={{ mt: 1, pl: 1.5, borderLeft: '3px solid', borderColor: 'warning.main', fontSize: '0.95rem' }}
            >
              Connection {segment.flight_number} ({route(segment.origin, segment.destination)}) will be missed.
            </Typography>
          ))}
        </Section>
      ) : null}

      {benefits.length > 0 ? (
        <Section title="Your benefits">
          <Box component="ul" sx={{ m: 0, pl: 2.5 }}>
            {benefits.map((label) => (
              <li key={label}>{label}</li>
            ))}
          </Box>
        </Section>
      ) : null}

      {option ? (
        <Section title="Proposed option">
          <OptionSummary option={option} />
        </Section>
      ) : null}

      {decision.decision.requires_human ? (
        <Section title="Next step">
          <Typography>An agent will review and confirm before any change is made.</Typography>
          {reasons.length > 0 ? (
            <Box component="ul" sx={{ m: 0, mt: 0.5, pl: 2.5, color: 'text.secondary' }}>
              {reasons.map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
            </Box>
          ) : null}
        </Section>
      ) : null}

      {canConfirm && option ? (
        <Section title="Next step">
          <Typography>{nextStepText('CONFIRM_OPTION')}</Typography>
          <Button
            variant="contained"
            sx={{ mt: 1.5 }}
            disabled={confirmDisabled}
            onClick={() => onConfirm?.(option)}
          >
            Confirm this option
          </Button>
        </Section>
      ) : null}

      {otherStepText ? (
        <Section title="Next step">
          <Typography>{otherStepText}</Typography>
        </Section>
      ) : null}

      {decision.degraded ? (
        <Typography variant="caption" color="text.secondary" component="p" sx={{ mt: 2, mb: 0 }}>
          This answer was prepared by our standard assistant.
        </Typography>
      ) : null}

      {policyRef || caseId ? (
        <Box sx={{ mt: 2.5, pt: 1.5, borderTop: '1px solid', borderColor: 'divider', display: 'grid', gap: 0.5 }}>
          {policyRef ? <Reference label="Policy reference" value={policyRef} /> : null}
          {caseId ? <Reference label="Case reference" value={caseId} /> : null}
        </Box>
      ) : null}
    </Paper>
  )
}
