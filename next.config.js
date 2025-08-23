/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  // Exclude api directory from build (it's a separate Express server)
  webpack: (config) => {
    config.resolve.fallback = {
      ...config.resolve.fallback,
      fs: false,
    }
    return config
  },
  // Exclude api directory from type checking
  typescript: {
    ignoreBuildErrors: false,
  },
}

module.exports = nextConfig
