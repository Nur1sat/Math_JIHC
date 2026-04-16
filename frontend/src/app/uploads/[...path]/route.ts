import { NextRequest } from "next/server";

import { getServerApiBaseUrl } from "@/lib/server-env";

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  const { path } = await context.params;
  const upstreamUrl = new URL(`/uploads/${path.join("/")}${request.nextUrl.search}`, getServerApiBaseUrl());
  const upstream = await fetch(upstreamUrl, {
    cache: "force-cache"
  });

  return new Response(upstream.body, {
    status: upstream.status,
    headers: upstream.headers
  });
}
