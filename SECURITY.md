# Security Policy

## Overview

This document outlines the security measures implemented in the CapSight CRE valuation platform to ensure data protection, access control, and compliance with industry standards.

## Security Headers

The application implements comprehensive security headers via `middleware.ts`:

### Content Security Policy (CSP)
- **Directives**: Strict CSP with allowlists for trusted sources
- **Frame Protection**: Prevents clickjacking attacks
- **Script Sources**: Only self-hosted and trusted CDN scripts allowed
- **Style Sources**: Inline styles allowed with nonce for flexibility
- **Connect Sources**: API calls restricted to same origin and Supabase

### Additional Security Headers
- **X-Content-Type-Options**: `nosniff` - Prevents MIME type sniffing
- **X-Frame-Options**: `DENY` - Blocks iframe embedding entirely  
- **Referrer-Policy**: `strict-origin-when-cross-origin` - Limits referrer leakage
- **Permissions-Policy**: Restricts access to sensitive browser features

## Authentication & Authorization

### Admin Console Protection
- **Token-Based Access**: Admin routes protected by `ADMIN_TOKEN` environment variable
- **Middleware Enforcement**: All `/admin/*` routes require valid token in `Authorization` header
- **Session Management**: Stateless token validation on each request

### Database Security
- **Row Level Security (RLS)**: Enabled on all sensitive tables
- **Service Role**: Admin operations use service role with elevated permissions
- **Connection Security**: All database connections over TLS

## Rate Limiting

### API Protection
- **Request Limits**: 100 requests per 15-minute window per IP
- **Token Bucket Algorithm**: Smooth rate limiting with burst allowance
- **Status Codes**: Proper HTTP 429 responses when limits exceeded

### Admin Console
- **Extended Limits**: Higher rate limits for admin operations
- **Protected Routes**: Rate limiting applied to all admin endpoints

## Data Protection

### In Transit
- **HTTPS Enforcement**: All connections require TLS 1.2+
- **HSTS Headers**: Strict Transport Security enabled
- **Certificate Pinning**: Recommended for production deployments

### At Rest
- **Database Encryption**: Supabase provides encryption at rest
- **Backup Security**: Automated encrypted backups
- **Key Management**: Environment-based secrets management

## Input Validation

### CSV Upload Security
- **File Type Validation**: Strict MIME type checking
- **Size Limits**: Maximum file size restrictions
- **Content Scanning**: Malicious content detection
- **Schema Validation**: Strict column and data type validation

### API Input Sanitization
- **SQL Injection Protection**: Parameterized queries via Supabase
- **XSS Prevention**: Input sanitization and output encoding
- **Type Validation**: Strict TypeScript type checking

## Monitoring & Logging

### Security Monitoring
- **Failed Login Attempts**: Rate limiting protects against brute force
- **Anomaly Detection**: Unusual access patterns flagged
- **Real-time Alerts**: Critical security events trigger notifications

### Audit Logging
- **Admin Actions**: All admin console actions logged
- **Data Access**: Sensitive data access tracked
- **Compliance**: Audit trail for regulatory requirements

## Vulnerability Management

### Dependency Security
- **Automated Scanning**: Regular dependency vulnerability scans
- **Update Policy**: Critical security patches applied within 48 hours
- **Version Pinning**: Controlled dependency versions

### Security Testing
- **Static Analysis**: Code security scanning in CI/CD pipeline
- **Penetration Testing**: Regular security assessments
- **Vulnerability Disclosure**: Responsible disclosure program

## Compliance

### Data Privacy
- **GDPR Compliance**: Data protection by design and default
- **Data Minimization**: Only necessary data collected and retained
- **Right to Deletion**: User data deletion capabilities

### Industry Standards
- **SOC 2 Type II**: Supabase infrastructure compliance
- **ISO 27001**: Information security management
- **OWASP Top 10**: Protection against common vulnerabilities

## Production Hardening

### Environment Security
- **Secret Management**: Environment variables for sensitive data
- **Network Security**: VPC isolation and firewall rules
- **Access Control**: Principle of least privilege

### Deployment Security
- **Blue-Green Deployment**: Zero-downtime secure deployments
- **Container Security**: Minimal base images and security scanning
- **Infrastructure as Code**: Auditable infrastructure definitions

## Header Relaxation for Development

In development environments, certain CSP restrictions may be relaxed for tools like Next.js dev server, hot reloading, and browser extensions. These relaxations are automatically removed in production builds.

### Development Allowances
- **Unsafe Eval**: Allowed for webpack dev server
- **Localhost Sources**: Local development server connections
- **Dev Tools**: Browser developer extension support

## Security Contact

For security concerns or vulnerability reports:

- **Email**: security@capsight.com
- **Response Time**: 24 hours for critical issues
- **Encryption**: PGP key available on request

## Security Updates

This security policy is reviewed quarterly and updated as needed. All security-related changes are documented in the changelog with appropriate severity levels.

---

**Last Updated**: January 2025  
**Version**: 1.0  
**Next Review**: April 2025
