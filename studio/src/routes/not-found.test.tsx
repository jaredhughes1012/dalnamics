import { screen } from '@testing-library/react'
import { renderRoute } from '@/test/render'

describe('not found', () => {
  it('shows a centered not-found page for unknown paths', async () => {
    renderRoute('/does-not-exist')

    expect(await screen.findByText('Page not found')).toBeInTheDocument()
    expect(screen.getByRole('main')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Go to dashboard' })).toHaveAttribute('href', '/')
  })
})
