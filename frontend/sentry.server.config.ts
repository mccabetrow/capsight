import * as Sentry from '@sentry/nextjs'

Sentry.init({
  dsn: process.env.SENTRY_DSN,
  
  // Performance monitoring  
  tracesSampleRate: 0.1, // 10% of transactions
  
  // Environment
  environment: process.env.NODE_ENV || 'development',
  
  // Release tracking
  release: process.env.VERCEL_GIT_COMMIT_SHA || 'dev',
  
  // Custom tags
  initialScope: {
    tags: {
      component: 'capsight-api',
    },
  },
})
