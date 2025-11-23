/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    // Default to docker internal URL, fallback to localhost for local dev
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';
    
    console.log(`Proxying requests to: ${backendUrl}`);

    return [
      // 1. API & Auth
      { source: '/api/:path*', destination: `${backendUrl}/:path*` },
      { source: '/token', destination: `${backendUrl}/token` },
      { source: '/staff/login', destination: `${backendUrl}/staff/login` },
      
      // 2. DATA ENDPOINTS (This fixes the empty lists!)
      { source: '/staff', destination: `${backendUrl}/staff/` },           // Fetch all staff
      { source: '/staff/:path*', destination: `${backendUrl}/staff/:path*` }, // Fetch specific staff
      
      { source: '/bookings', destination: `${backendUrl}/bookings` },      // Fetch all bookings
      { source: '/bookings/:path*', destination: `${backendUrl}/bookings/:path*` },
      
      { source: '/clients', destination: `${backendUrl}/clients` },        // Fetch all clients
      { source: '/clients/:path*', destination: `${backendUrl}/clients/:path*` },
      
      { source: '/pets', destination: `${backendUrl}/pets` },
      { source: '/pets/:path*', destination: `${backendUrl}/pets/:path*` },
      
      { source: '/surgeries', destination: `${backendUrl}/surgeries` },
      { source: '/surgeries/:path*', destination: `${backendUrl}/surgeries/:path*` },
      
      { source: '/medications', destination: `${backendUrl}/medications` },
      { source: '/medications/:path*', destination: `${backendUrl}/medications/:path*` },
      
      // 3. AI & Docs
      { source: '/suggest_slots', destination: `${backendUrl}/suggest_slots` },
      { source: '/chat', destination: `${backendUrl}/chat` },
      { source: '/agent/:path*', destination: `${backendUrl}/agent/:path*` },
      { source: '/docs', destination: `${backendUrl}/docs` },
      { source: '/openapi.json', destination: `${backendUrl}/openapi.json` }
    ];
  },
};

export default nextConfig;