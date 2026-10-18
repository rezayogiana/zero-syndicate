/**
 * ZERO SYNDICATE — Cloudflare Pages Function
 * Receives same-origin /api/* requests from app.js and forwards to the Python API.
 * Set BACKEND_URL in Cloudflare Pages > Settings > Variables and Secrets.
 * Example: https://your-api.onrender.com
 */
export async function onRequest({ request, env }) {
  if (!env.BACKEND_URL) {
    return Response.json(
      { detail: "Backend belum dikonfigurasi. Atur BACKEND_URL di Cloudflare Pages." },
      { status: 503, headers: { "Cache-Control": "no-store" } }
    );
  }
  const original = new URL(request.url);
  const path = original.pathname;
  if (!/^\/api\/(health|astro|calendar|analyst)\/?$/.test(path)) {
    return Response.json({ detail: "API endpoint tidak dikenal" }, { status: 404 });
  }
  if (!(request.method === "GET" || (request.method === "POST" && path === "/api/analyst"))) {
    return Response.json({ detail: "Method tidak diizinkan" }, { status: 405 });
  }
  try {
    const backend = new URL(env.BACKEND_URL);
    if (backend.protocol !== "https:") throw new Error("BACKEND_URL harus HTTPS");
    const target = new URL(path + original.search, backend.origin);
    const forwardedHeaders = new Headers(request.headers);
    forwardedHeaders.delete("cookie");
    forwardedHeaders.delete("authorization");
    forwardedHeaders.delete("host");
    const upstream = new Request(target.toString(), {
      method: request.method,
      headers: forwardedHeaders,
      body: request.method === "GET" ? undefined : request.body,
      redirect: "follow",
    });
    const result = await fetch(upstream);
    const headers = new Headers(result.headers);
    headers.set("Cache-Control", "no-store");
    headers.delete("set-cookie");
    return new Response(result.body, { status: result.status, headers });
  } catch (err) {
    return Response.json(
      { detail: "Koneksi ke layanan analis belum tersedia. Silakan coba kembali." },
      { status: 502, headers: { "Cache-Control": "no-store" } }
    );
  }
}
