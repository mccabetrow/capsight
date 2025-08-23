import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

// Simple in-memory rate limiter (for development)
// In production, use Redis with @upstash/ratelimit
const rateLimitMap = new Map<string, { count: number; resetTime: number }>()

const RATE_LIMIT_WINDOW = 60 * 1000 // 1 minute
const RATE_LIMIT_MAX_REQUESTS = 60 // 60 requests per minute

export function middleware(request: NextRequest) {
  const response = NextResponse.next()

  // Security Headers
  const csp = [
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline' vercel.live plausible.io *.vercel-insights.com",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: https:",
    "connect-src 'self' https://*.supabase.co https://*.ingest.sentry.io",
    "font-src 'self' data:",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
    "block-all-mixed-content",
    "upgrade-insecure-requests"
  ].join('; ')

  response.headers.set('Content-Security-Policy', csp)
  response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin')
  response.headers.set('Permissions-Policy', 'geolocation=(), microphone=(), camera=()')
  response.headers.set('X-Content-Type-Options', 'nosniff')
  response.headers.set('X-Frame-Options', 'DENY')
  response.headers.set('X-XSS-Protection', '1; mode=block')

  // Admin route protection
  if (request.nextUrl.pathname.startsWith('/admin')) {
    const adminToken = request.headers.get('x-admin-token') || 
                      request.cookies.get('admin-token')?.value ||
                      request.nextUrl.searchParams.get('token')

    if (!adminToken || adminToken !== process.env.ADMIN_TOKEN) {
      return new NextResponse('Unauthorized', { 
        status: 401,
        headers: {
          'WWW-Authenticate': 'Bearer realm="Admin Console"'
        }
      })
    }

    // Set admin token cookie for subsequent requests
    if (adminToken === process.env.ADMIN_TOKEN) {
      response.cookies.set('admin-token', adminToken, {
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'strict',
        maxAge: 60 * 60 * 24 // 24 hours
      })
    }
  }

  // Rate limiting for API routes
  if (request.nextUrl.pathname.startsWith('/api/value')) {
    const ip = request.ip || request.headers.get('x-forwarded-for') || '127.0.0.1'
    const key = `ratelimit:${ip}`
    const now = Date.now()

    let rateLimitData = rateLimitMap.get(key)
    
    if (!rateLimitData || now > rateLimitData.resetTime) {
      rateLimitData = {
        count: 1,
        resetTime: now + RATE_LIMIT_WINDOW
      }
      rateLimitMap.set(key, rateLimitData)
      
      response.headers.set('X-RateLimit-Limit', RATE_LIMIT_MAX_REQUESTS.toString())
      response.headers.set('X-RateLimit-Remaining', (RATE_LIMIT_MAX_REQUESTS - 1).toString())
      response.headers.set('X-RateLimit-Reset', Math.ceil(rateLimitData.resetTime / 1000).toString())
      
      return response
    }

    if (rateLimitData.count >= RATE_LIMIT_MAX_REQUESTS) {
      return new NextResponse(JSON.stringify({ error: 'Rate limit exceeded' }), {
        status: 429,
        headers: {
          'Content-Type': 'application/json',
          'X-RateLimit-Limit': RATE_LIMIT_MAX_REQUESTS.toString(),
          'X-RateLimit-Remaining': '0',
          'X-RateLimit-Reset': Math.ceil(rateLimitData.resetTime / 1000).toString(),
          'Retry-After': Math.ceil((rateLimitData.resetTime - now) / 1000).toString()
        }
      })
    }

    rateLimitData.count++
    rateLimitMap.set(key, rateLimitData)

    response.headers.set('X-RateLimit-Limit', RATE_LIMIT_MAX_REQUESTS.toString())
    response.headers.set('X-RateLimit-Remaining', (RATE_LIMIT_MAX_REQUESTS - rateLimitData.count).toString())
    response.headers.set('X-RateLimit-Reset', Math.ceil(rateLimitData.resetTime / 1000).toString())
  }

  return response
}

export const config = {
  matcher: [
    '/admin/:path*',
    '/api/value/:path*'
  ]
}
