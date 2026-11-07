import { act, fireEvent, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { renderWithTheme } from '../../../testUtils'
import { Composer } from './Composer'
import { MAX_MESSAGE_LENGTH, SUGGESTED_QUESTIONS } from './composerConfig'

function getInput() {
  return screen.getByRole('textbox', { name: 'Your question' })
}

function getSendButton() {
  return screen.getByRole('button', { name: 'Send message' })
}

function setup(onSubmit: (message: string) => void | Promise<void> = vi.fn()) {
  const user = userEvent.setup({ delay: null })
  renderWithTheme(<Composer onSubmit={onSubmit} />)
  return { user, onSubmit }
}

describe('Composer input', () => {
  it('shows the placeholder when empty', () => {
    setup()

    expect(screen.getByPlaceholderText('Ask about your flight change...')).toBeInTheDocument()
  })

  it('is a multiline input', () => {
    setup()

    expect(getInput().tagName).toBe('TEXTAREA')
  })

  it('has an accessible name and a labeled send button', () => {
    setup()

    expect(getInput()).toBeInTheDocument()
    expect(getSendButton()).toBeInTheDocument()
  })
})

describe('Composer sending', () => {
  it('sends the trimmed text with the button', async () => {
    const { user, onSubmit } = setup()

    await user.type(getInput(), '  What are my options?  ')
    await user.click(getSendButton())

    expect(onSubmit).toHaveBeenCalledTimes(1)
    expect(onSubmit).toHaveBeenCalledWith('What are my options?')
  })

  it('sends with Enter without adding a line break', async () => {
    const { user, onSubmit } = setup()

    await user.type(getInput(), 'Is my flight delayed?{Enter}')

    expect(onSubmit).toHaveBeenCalledWith('Is my flight delayed?')
    expect(getInput()).toHaveValue('')
  })

  it('inserts a line break with Shift+Enter and sends nothing', async () => {
    const { user, onSubmit } = setup()

    await user.type(getInput(), 'First{Shift>}{Enter}{/Shift}Second')

    expect(getInput()).toHaveValue('First\nSecond')
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('does not send when Enter only confirms an input-method composition', () => {
    const onSubmit = vi.fn()
    renderWithTheme(<Composer onSubmit={onSubmit} />)
    fireEvent.change(getInput(), { target: { value: 'ni' } })

    fireEvent.keyDown(getInput(), { key: 'Enter', isComposing: true })
    fireEvent.keyDown(getInput(), { key: 'Enter', keyCode: 229 })

    expect(onSubmit).not.toHaveBeenCalled()
    expect(getInput()).toHaveValue('ni')
  })

  it('does not send blank text and disables the button', async () => {
    const { user, onSubmit } = setup()

    expect(getSendButton()).toBeDisabled()
    await user.type(getInput(), '   {Enter}')

    expect(getSendButton()).toBeDisabled()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('clears the input after sending', async () => {
    const { user } = setup()

    await user.type(getInput(), 'Hello')
    await user.click(getSendButton())

    expect(getInput()).toHaveValue('')
  })

  it('keeps the text when sending fails so it can be sent again', async () => {
    const onSubmit = vi.fn().mockRejectedValue(new Error('network'))
    const { user } = setup(onSubmit)

    await user.type(getInput(), 'Hello')
    await user.click(getSendButton())

    expect(getInput()).toHaveValue('Hello')
  })

  it('does not send twice while the first send is pending', async () => {
    let finish: () => void = () => {}
    const onSubmit = vi.fn(() => new Promise<void>((resolve) => (finish = resolve)))
    const { user } = setup(onSubmit)

    await user.type(getInput(), 'Hello')
    await user.click(getSendButton())
    await user.type(getInput(), '{Enter}')

    expect(onSubmit).toHaveBeenCalledTimes(1)
    await act(async () => finish())
  })
})

describe('Composer disabled state', () => {
  it('blocks the input, the send button and the suggestions', () => {
    renderWithTheme(<Composer disabled onSubmit={vi.fn()} />)

    expect(getInput()).toBeDisabled()
    expect(getSendButton()).toBeDisabled()
    for (const question of SUGGESTED_QUESTIONS) {
      // A MUI chip is a div with role=button, so it exposes aria-disabled instead of disabled.
      expect(screen.getByRole('button', { name: question })).toHaveAttribute('aria-disabled', 'true')
    }
  })

  it('ignores a click on a suggestion', () => {
    renderWithTheme(<Composer disabled onSubmit={vi.fn()} />)

    fireEvent.click(screen.getByRole('button', { name: 'What are my options?' }))

    expect(getInput()).toHaveValue('')
  })
})

describe('Composer length limit', () => {
  it('has a maxLength of 500 on the input', () => {
    setup()

    expect(getInput()).toHaveAttribute('maxlength', String(MAX_MESSAGE_LENGTH))
  })

  it('does not accept typing past the limit', async () => {
    const { user } = setup()
    fireEvent.change(getInput(), { target: { value: 'a'.repeat(MAX_MESSAGE_LENGTH) } })

    await user.type(getInput(), 'b')

    expect(getInput()).toHaveValue('a'.repeat(MAX_MESSAGE_LENGTH))
  })

  it('keeps only the first 500 characters of a pasted text', async () => {
    const { user } = setup()

    await user.click(getInput())
    await user.paste('x'.repeat(700))

    expect(getInput()).toHaveValue('x'.repeat(MAX_MESSAGE_LENGTH))
  })

  it('truncates a change that skips the maxLength attribute', () => {
    setup()

    fireEvent.change(getInput(), { target: { value: 'y'.repeat(700) } })

    expect(getInput()).toHaveValue('y'.repeat(MAX_MESSAGE_LENGTH))
  })

  it('shows the counter from 400 characters and not at 399', () => {
    setup()

    fireEvent.change(getInput(), { target: { value: 'a'.repeat(399) } })
    expect(screen.queryByText(/\/500$/)).not.toBeInTheDocument()

    fireEvent.change(getInput(), { target: { value: 'a'.repeat(400) } })
    expect(screen.getByText('400/500')).toBeInTheDocument()
  })

  it('hides the counter after sending', async () => {
    const { user } = setup()
    fireEvent.change(getInput(), { target: { value: 'a'.repeat(450) } })
    expect(screen.getByText('450/500')).toBeInTheDocument()

    await user.click(getSendButton())

    expect(screen.queryByText(/\/500$/)).not.toBeInTheDocument()
  })
})

describe('Composer suggestions', () => {
  it('offers the three suggested questions', () => {
    setup()

    for (const question of SUGGESTED_QUESTIONS) {
      expect(screen.getByRole('button', { name: question })).toBeInTheDocument()
    }
    expect(SUGGESTED_QUESTIONS).toHaveLength(3)
  })

  it('puts the suggestion in the input, focuses it and sends nothing', async () => {
    const { user, onSubmit } = setup()

    await user.click(screen.getByRole('button', { name: 'What are my options?' }))

    expect(getInput()).toHaveValue('What are my options?')
    expect(getInput()).toHaveFocus()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('replaces text that was already in the input', async () => {
    const { user } = setup()
    await user.type(getInput(), 'Something else')

    await user.click(screen.getByRole('button', { name: 'Can I ask for compensation?' }))

    expect(getInput()).toHaveValue('Can I ask for compensation?')
  })
})
