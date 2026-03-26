import { render, screen } from '@testing-library/react'
import Sidebar from '@/components/Sidebar'
import { vi } from 'vitest'

// Mock next/navigation
vi.mock('next/navigation', () => ({
  usePathname: () => '/',
}))

// Mock next/link to just render an anchor tag
vi.mock('next/link', () => {
  return {
    __esModule: true,
    default: ({ children, href, className }: any) => {
      return (
        <a href={href} className={className}>
          {children}
        </a>
      )
    },
  }
})

describe('Sidebar', () => {
  it('renders the brand title', () => {
    render(<Sidebar />)
    expect(screen.getByText('geekPR')).toBeInTheDocument()
    expect(screen.getByText('Autonomous Review')).toBeInTheDocument()
  })

  it('renders all navigation items', () => {
    render(<Sidebar />)
    expect(screen.getByText('Feed')).toBeInTheDocument()
    expect(screen.getByText('Analytics')).toBeInTheDocument()
    expect(screen.getByText('Activity')).toBeInTheDocument()
    expect(screen.getByText('Settings')).toBeInTheDocument()
  })

  it('highlights the active link based on pathname', () => {
    render(<Sidebar />)
    // Since we mocked usePathname to return '/', Feed should be active.
    const feedLink = screen.getByText('Feed').closest('a')
    expect(feedLink).toHaveClass('bg-white/[0.07]')
    
    // Analytics should not be active
    const analyticsLink = screen.getByText('Analytics').closest('a')
    expect(analyticsLink).not.toHaveClass('bg-white/[0.07]')
  })
})
