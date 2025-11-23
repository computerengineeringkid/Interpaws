/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';
    console.log(`Proxying requests to: ${backendUrl}`);

    return [
      // 1. API & Auth Routes
      { source: '/api/:path*', destination: `${backendUrl}/:path*` },
      { source: '/token', destination: `${backendUrl}/token` },
      { source: '/staff/login', destination: `${backendUrl}/staff/login` }, // Critical for admin login
      
      // 2. Core Business Entities (The missing link!)
      { source: '/staff/:path*', destination: `${backendUrl}/staff/:path*` },
      { source: '/bookings/:path*', destination: `${backendUrl}/bookings/:path*` },
      { source: '/clients/:path*', destination: `${backendUrl}/clients/:path*` },
      { source: '/pets/:path*', destination: `${backendUrl}/pets/:path*` },
      { source: '/surgeries/:path*', destination: `${backendUrl}/surgeries/:path*` },
      { source: '/medications/:path*', destination: `${backendUrl}/medications/:path*` },
      { source: '/preferences/:path*', destination: `${backendUrl}/preferences/:path*` },
      
      // 3. AI & Admin Specifics
      { source: '/admin/:path*', destination: `${backendUrl}/admin/:path*` }, // Careful: this proxies backend admin routes, ensure no conflict with frontend pages
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