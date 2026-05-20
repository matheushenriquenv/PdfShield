/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Redirecionar /api/downloads/:token → backend
  async rewrites() {
    return [
      {
        source: '/api/downloads/:token',
        destination: `${process.env.BACKEND_URL}/api/downloads/:token`,
      },
    ]
  },
}

module.exports = nextConfig
