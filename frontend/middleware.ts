import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const token = request.cookies.get('aura_token')?.value;
  const { pathname } = request.nextUrl;

  // Define public files/assets/paths that should never be protected or redirected
  if (
    pathname.startsWith('/api') ||
    pathname.startsWith('/_next') ||
    pathname.includes('.') ||
    pathname === '/login'
  ) {
    // If logged in and trying to access /login, redirect to /dashboard
    if (token && pathname === '/login') {
      return NextResponse.redirect(new URL('/dashboard', request.url));
    }
    return NextResponse.next();
  }

  // For any other route (which includes /, /dashboard, /devices, /models, /scripts, /deployments, /monitoring)
  if (!token) {
    return NextResponse.redirect(new URL('/login', request.url));
  }

  return NextResponse.next();
}
