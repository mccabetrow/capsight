import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

// Simple in-memory rate limiter (for development)
// In production, use Redis with @upstash/ratelimit
const rateLimitMap = new Map<string, { count: number; resetTime: number }>()

const RATE_LIMIT_WINDOW = 60 * 1000 // 1 minute
const RATE_LIMIT_MAX_REQUESTS = 60 // 60 requests per minute

export function middleware(request: NextRequest) {
  // Only apply rate limiting to /api/value endpoint
  if (!request.nextUrl.pathname.startsWith('/api/value')) {
    return NextResponse.next()
  }

  const ip = request.ip || request.headers.get('x-forwarded-for') || '127.0.0.1'
  const key = `ratelimit:${ip}`
  const now = Date.now()

  // Get or initialize rate limit data
  let rateLimitData = rateLimitMap.get(key)
  
  if (!rateLimitData || now > rateLimitData.resetTime) {
    // Reset or initialize
    rateLimitData = {
      count: 1,
      resetTime: now + RATE_LIMIT_WINDOW
    }
    rateLimitMap.set(key, rateLimitData)
    
    return NextResponse.next()
  }

  if (rateLimitData.count >= RATE_LIMIT_MAX_REQUESTS) {
    // Rate limit exceeded
    return new NextResponse('Rate limit exceeded', {
      status: 429,
      headers: {
        'X-RateLimit-Limit': RATE_LIMIT_MAX_REQUESTS.toString(),
        'X-RateLimit-Remaining': '0',
        'X-RateLimit-Reset': Math.ceil(rateLimitData.resetTime / 1000).toString(),
        'Retry-After': Math.ceil((rateLimitData.resetTime - now) / 1000).toString(),
        'Content-Type': 'application/json'
      }
    })
  }

  // Increment counter
  rateLimitData.count++
  rateLimitMap.set(key, rateLimitData)

  const response = NextResponse.next()
  response.headers.set('X-RateLimit-Limit', RATE_LIMIT_MAX_REQUESTS.toString())
  response.headers.set('X-RateLimit-Remaining', (RATE_LIMIT_MAX_REQUESTS - rateLimitData.count).toString())
  response.headers.set('X-RateLimit-Reset', Math.ceil(rateLimitData.resetTime / 1000).toString())

  return response
}

export const config = {
  matcher: '/api/value/:path*'
}
