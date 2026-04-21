/**
 * Next.js middleware — enforces basegeek SSO at the edge.
 *
 * Runs before any page renders. If the incoming request is missing the
 * basegeek session cookie (`geek_token`, Domain=.clintgeek.com), we 302
 * the user straight to basegeek's login page with a `redirect` back to
 * the URL they were trying to reach. No geekPR UI flashes before the
 * redirect; no way to even render the dashboard shell unauthenticated.
 *
 * Paths matched are defined in `config.matcher` below. API routes,
 * Next.js internals, and static assets are deliberately excluded — the
 * backend enforces auth on /api/* itself, and bouncing static assets
 * would thrash the redirect loop.
 *
 * When BASEGEEK_AUTH_ENABLED is not "true" the middleware becomes a
 * pass-through (mirrors the backend's bypass mode) so local dev and
 * self-hosted deployments without basegeek can still use the dashboard
 * behind whatever upstream auth the operator wires up.
 */

import { NextRequest, NextResponse } from "next/server";

const SESSION_COOKIE =
  process.env.NEXT_PUBLIC_BASEGEEK_SESSION_COOKIE || "geek_token";
const LOGIN_URL =
  process.env.NEXT_PUBLIC_BASEGEEK_LOGIN_URL || "https://basegeek.clintgeek.com/";
const AUTH_ENABLED =
  (process.env.NEXT_PUBLIC_BASEGEEK_AUTH_ENABLED || "true").toLowerCase() === "true";

export function middleware(request: NextRequest) {
  if (!AUTH_ENABLED) return NextResponse.next();

  if (request.cookies.get(SESSION_COOKIE)) {
    return NextResponse.next();
  }

  const returnTo = encodeURIComponent(request.url);
  const loginUrl = `${LOGIN_URL}?redirect=${returnTo}&app=geekpr`;
  return NextResponse.redirect(loginUrl);
}

export const config = {
  matcher: [
    // Protect every page path EXCEPT:
    //   /api/*          — backend handles its own auth
    //   /_next/static/* — Next build output (scripts, css)
    //   /_next/image/*  — image optimizer
    //   favicon.ico     — because browsers are going to ask for it anyway
    //   *.png/svg/ico   — public static assets if any
    "/((?!api|_next/static|_next/image|favicon.ico|.*\\.(?:png|jpg|jpeg|svg|ico|webp|gif)).*)",
  ],
};
