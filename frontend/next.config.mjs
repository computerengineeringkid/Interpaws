/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    // This uses the Docker internal name 'http://backend:8000' when running in Docker
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';
    
    console.log(`Proxying requests to: ${backendUrl}`);

    return [
      // API endpoints
      {
        source: '/api/:path*',
        destination: `${backendUrl}/:path*`,
      },
      // Client Login (The missing piece!)
      {
        source: '/token',
        destination: `${backendUrl}/token`,
      },
      // Staff/Admin Login
      {
        source: '/staff/token',
        destination: `${backendUrl}/staff/token`,
      },
      // API Documentation (Swagger UI)
      {
        source: '/docs',
        destination: `${backendUrl}/docs`,
      },
      {
        source: '/openapi.json',
        destination: `${backendUrl}/openapi.json`,
      }
    ];
  },
};

export default nextConfig;