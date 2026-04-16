import { NextRequest } from "next/server";

const API_BASE_URL = process.env.NEXT_SERVER_API_URL ?? "http://127.0.0.1:8000";

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  const { path } = await context.params;
  const upstream = await fetch(`${API_BASE_URL}/uploads/${path.join("/")}${request.nextUrl.search}`, {
    cache: "force-cache"
  });

  return new Response(upstream.body, {
    status: upstream.status,
    headers: upstream.headers
  });
}
