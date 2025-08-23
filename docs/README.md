# CapSight Documentation Site

A Next.js-powered documentation site for CapSight's commercial real estate valuation platform.

## Overview

This documentation site provides:

- **Methodology**: Detailed explanation of our valuation approach
- **API Reference**: Interactive OpenAPI documentation
- **Operations Guide**: Deployment and maintenance procedures
- **Accuracy & SLA**: Performance metrics and service level agreements
- **Changelog**: Version history and updates

## Getting Started

### Prerequisites

- Node.js 18+ 
- npm or yarn

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Start production server
npm start
```

## Features

### MDX Content
- Write documentation in Markdown with JSX components
- Syntax highlighting for code blocks
- Custom components for callouts, warnings, etc.

### OpenAPI Integration
- Automatic API reference generation from OpenAPI spec
- Interactive API explorer
- Up-to-date with backend changes

### Responsive Design
- Mobile-first responsive layout
- Tailwind CSS for styling
- Clean, professional design

## Content Structure

```
docs/
├── pages/
│   ├── index.tsx          # Homepage
│   ├── methodology.tsx    # Valuation methodology
│   ├── api-reference.tsx  # OpenAPI docs
│   ├── operations.tsx     # Ops guide
│   ├── accuracy.tsx       # SLA and accuracy
│   └── changelog.tsx      # Version history
├── components/
│   └── Layout.tsx         # Site layout
├── public/
│   └── openapi.yaml       # API specification
└── styles/
    └── globals.css        # Global styles
```

## Updating Content

### Methodology & Operations
Content is imported from the main project's markdown files:
- `../../VALUATION_METHOD.md`
- `../../ENHANCED_OPERATIONS_PLAYBOOK.md`

### API Documentation
The OpenAPI spec is automatically copied from the backend during build:
- Source: `../../openapi.yaml`
- Destination: `public/openapi.yaml`

### Changelog
Update the changelog page with new releases and features.

## Deployment

### Development
```bash
npm run dev
```
Visit http://localhost:3001

### Production Build
```bash
npm run build
npm start
```

### Static Export (optional)
```bash
npm run build
npm run export
```

## Configuration

### Next.js Config
- TypeScript support
- Tailwind CSS integration
- Custom port (3001) to avoid conflicts

### Environment Variables
None required - all content is static.

## Customization

### Styling
- Tailwind CSS classes in components
- Global styles in `styles/globals.css`
- Theme colors match CapSight branding

### Layout
- Responsive navigation
- Search functionality (planned)
- Dark mode support (planned)

### Components
- Reusable documentation components
- Syntax highlighting
- Code examples
- API explorer integration

## Contributing

1. Add/edit content in the appropriate page files
2. Test locally with `npm run dev`
3. Submit pull request

## License

Internal documentation - CapSight, LLC
