import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

export function middleware(request: NextRequest) {
  if (request.nextUrl.pathname === "/admin") {
    const host = request.headers.get("host") ?? request.nextUrl.host;
    const protocol = request.headers.get("x-forwarded-proto") ?? request.nextUrl.protocol.replace(":", "");
    const url = new URL(`${protocol}://${host}/admin/login`);
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/admin"]
};
