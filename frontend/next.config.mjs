/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    // Use the Docker service name 'http://backend:8000' or localhost fallback
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';
    
    console.log(`Proxying requests to: ${backendUrl}`);

    return [
      // 1. API & Auth Routes
      { source: '/api/:path*', destination: `${backendUrl}/:path*` },
      { source: '/token', destination: `${backendUrl}/token` },
      { source: '/staff/login', destination: `${backendUrl}/staff/login` },
      
      // 2. Core Business Entities (This fixes the empty Staff/Bookings lists)
      { source: '/staff/:path*', destination: `${backendUrl}/staff/:path*` },
      { source: '/bookings/:path*', destination: `${backendUrl}/bookings/:path*` },
      { source: '/clients/:path*', destination: `${backendUrl}/clients/:path*` },
      { source: '/pets/:path*', destination: `${backendUrl}/pets/:path*` },
      { source: '/surgeries/:path*', destination: `${backendUrl}/surgeries/:path*` },
      { source: '/medications/:path*', destination: `${backendUrl}/medications/:path*` },
      { source: '/preferences/:path*', destination: `${backendUrl}/preferences/:path*` },
      
      // 3. AI & Admin Specifics
      { source: '/agent/:path*', destination: `${backendUrl}/agent/:path*` },
      { source: '/chat/:path*', destination: `${backendUrl}/chat/:path*` },
      { source: '/suggest_slots', destination: `${backendUrl}/suggest_slots` },
      { source: '/log-feedback', destination: `${backendUrl}/log-feedback` },
      
      // 4. Documentation
      { source: '/docs', destination: `${backendUrl}/docs` },
      { source: '/openapi.json', destination: `${backendUrl}/openapi.json` }
    ];
  },
};

export default nextConfig;