import { NextRequest } from "next/server";

import { getServerApiBaseUrls } from "@/lib/server-env";

function makeUpstreamUrl(baseUrl: string, path: string[], search: string) {
  return new URL(`/api/v1/${path.join("/")}${search}`, baseUrl);
}

function makeResponse(upstream: Response) {
  const responseHeaders = new Headers(upstream.headers);
  responseHeaders.delete("content-encoding");
  responseHeaders.delete("transfer-encoding");

  return new Response(upstream.body, {
    status: upstream.status,
    headers: responseHeaders
  });
}

async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  const { path } = await context.params;
  const headers = new Headers(request.headers);
  headers.delete("host");
  headers.delete("connection");
  headers.delete("content-length");
  headers.set("accept-encoding", "identity");

  const init: RequestInit = {
    method: request.method,
    headers,
    cache: "no-store"
  };

  if (!["GET", "HEAD"].includes(request.method)) {
    init.body = await request.arrayBuffer();
  }

  const upstreamUrls = getServerApiBaseUrls().map((baseUrl) =>
    makeUpstreamUrl(baseUrl, path, request.nextUrl.search)
  );
  let lastError: unknown;

  for (const upstreamUrl of upstreamUrls) {
    try {
      return makeResponse(await fetch(upstreamUrl, init));
    } catch (error) {
      lastError = error;
    }
  }

  console.error("API proxy failed for all upstreams", lastError);
  return Response.json({ detail: "Backend service unavailable" }, { status: 503 });
}

export { proxy as GET, proxy as POST, proxy as PUT, proxy as DELETE, proxy as PATCH };
