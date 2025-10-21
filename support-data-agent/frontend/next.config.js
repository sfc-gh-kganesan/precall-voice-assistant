/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Note: swcMinify is now the default in Next.js 15 and removed from config

  // Redirect root to dashboard
  async redirects() {
    return [
      {
        source: '/',
        destination: '/dashboard',
        permanent: false,
      },
    ]
  },

  // Specify workspace root to silence warning
  outputFileTracingRoot: __dirname,
}

module.exports = nextConfig
