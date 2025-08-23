import * as Sentry from '@sentry/nextjs'

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  
  // Performance monitoring
  tracesSampleRate: 0.1, // 10% of transactions
  
  // Session replay (optional)
  replaysSessionSampleRate: 0.01, // 1% of sessions
  replaysOnErrorSampleRate: 1.0, // 100% of error sessions
  
  // Environment
  environment: process.env.NODE_ENV || 'development',
  
  // Release tracking
  release: process.env.VERCEL_GIT_COMMIT_SHA || 'dev',
  
  // Filter out noisy errors
  beforeSend(event, hint) {
    // Filter out network errors
    if (event.exception?.values?.[0]?.type === 'NetworkError') {
      return null
    }
    
    // Filter out rate limit errors  
    if (event.exception?.values?.[0]?.value?.includes('Rate limit')) {
      return null
    }
    
    return event
  },
  
  // Custom tags
  initialScope: {
    tags: {
      component: 'capsight-frontend',
    },
  },
})
