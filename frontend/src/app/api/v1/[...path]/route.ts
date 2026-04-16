import { NextRequest } from "next/server";

const API_BASE_URL = process.env.NEXT_SERVER_API_URL ?? "http://127.0.0.1:8000";

async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  const { path } = await context.params;
  const upstreamUrl = new URL(
    `${API_BASE_URL}/api/v1/${path.join("/")}${request.nextUrl.search}`
  );
  const headers = new Headers(request.headers);
  headers.delete("host");
  headers.delete("connection");
  headers.delete("content-length");

  const init: RequestInit = {
    method: request.method,
    headers,
    cache: "no-store"
  };

  if (!["GET", "HEAD"].includes(request.method)) {
    init.body = await request.arrayBuffer();
  }

  const upstream = await fetch(upstreamUrl, init);
  const responseHeaders = new Headers(upstream.headers);
  responseHeaders.delete("content-encoding");
  responseHeaders.delete("transfer-encoding");

  return new Response(upstream.body, {
    status: upstream.status,
    headers: responseHeaders
  });
}

export { proxy as GET, proxy as POST, proxy as PUT, proxy as DELETE, proxy as PATCH };
