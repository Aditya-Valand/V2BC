/**
 * Next.js proxy (route protection).
 *
 * Rules:
 *  - /dashboard, /clients, /compliance, /deadlines, /reminders  → CA only
 *  - /home, /transactions, /evidence                             → Client only
 *  - /login, /register, /verify-otp, /invite/*                  → Public (no auth needed)
 *
 * Token presence is checked via cookie set on login.
 * Full role validation happens in each page component.
 */
import { NextResponse } from "next/server";

const PUBLIC_PATHS = ["/login", "/client-login", "/register", "/verify-otp", "/invite"];

export function proxy(request) {
  const { pathname } = request.nextUrl;

  const isPublic = PUBLIC_PATHS.some((p) => pathname.startsWith(p));
  if (isPublic) return NextResponse.next();

  const token = request.cookies.get("bc_access_token")?.value;

  if (!token) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("redirect", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/((?!api|_next/static|_next/image|favicon.ico|robots.txt).*)",
  ],
};
