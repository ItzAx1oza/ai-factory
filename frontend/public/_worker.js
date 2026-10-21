// Cloudflare Pages Advanced Mode: proxy /api/* to the Render backend.
// All non-API requests are served as ordinary static assets.
export default {
  async fetch(request, env) {
    const incoming = new URL(request.url);
    if (!incoming.pathname.startsWith('/api/')) {
      return env.ASSETS.fetch(request);
    }

    let backend;
    try {
      backend = new URL(env.BACKEND_URL || 'https://ai-factory-hmtu.onrender.com');
      if (backend.protocol !== 'https:' || backend.username || backend.password ||
          backend.search || backend.hash || backend.pathname !== '/') {
        return new Response('Invalid BACKEND_URL configuration', { status: 500 });
      }
    } catch {
      return new Response('Invalid BACKEND_URL configuration', { status: 500 });
    }

    const dest = new URL(incoming.pathname + incoming.search, backend.origin);
    const headers = new Headers();
    for (const name of ['authorization', 'content-type', 'accept']) {
      const value = request.headers.get(name);
      if (value) headers.set(name, value);
    }
    try {
      const response = await fetch(dest, {
        method: request.method,
        headers,
        body: request.method === 'GET' || request.method === 'HEAD' ? undefined : request.body,
        redirect: 'manual',
      });
      const responseHeaders = new Headers();
      for (const name of ['content-type', 'content-disposition']) {
        const value = response.headers.get(name);
        if (value) responseHeaders.set(name, value);
      }
      responseHeaders.set('cache-control', 'no-store');
      return new Response(response.body, { status: response.status, headers: responseHeaders });
    } catch {
      return new Response('Backend currently unavailable', { status: 502 });
    }
  },
};
