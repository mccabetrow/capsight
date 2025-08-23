import { render, screen } from '@testing-library/react'
import Home from '../pages/index'

// Mock SWR to avoid actual API calls in tests
jest.mock('swr', () => ({
  __esModule: true,
  default: jest.fn(() => ({
    data: null,
    error: null,
    isLoading: false,
  })),
}))

// Mock Supabase client
jest.mock('../lib/supabase', () => ({
  createClient: jest.fn(() => ({
    from: jest.fn(() => ({
      select: jest.fn(() => ({
        eq: jest.fn(() => Promise.resolve({ data: [], error: null })),
      })),
    })),
  })),
}))

describe('Home Page', () => {
  it('renders the main heading', () => {
    render(<Home />)
    
    const heading = screen.getByRole('heading', { name: /CapSight/i })
    expect(heading).toBeInTheDocument()
  })

  it('renders market selector', () => {
    render(<Home />)
    
    const marketSelect = screen.getByLabelText(/Select Market/i)
    expect(marketSelect).toBeInTheDocument()
  })

  it('renders NOI input', () => {
    render(<Home />)
    
    const noiInput = screen.getByLabelText(/Annual NOI/i)
    expect(noiInput).toBeInTheDocument()
  })

  it('shows placeholder text when no market selected', () => {
    render(<Home />)
    
    const placeholder = screen.getByText(/Select a market and enter NOI/i)
    expect(placeholder).toBeInTheDocument()
  })
})
