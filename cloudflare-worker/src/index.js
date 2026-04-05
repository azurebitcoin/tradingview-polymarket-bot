function jsonResponse(payload, status = 200) {
  return new Response(JSON.stringify(payload, null, 2), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
    },
  });
}

function normalizeBaseUrl(value) {
  return value.replace(/\/+$/, "");
}

function splitPath(pathname) {
  return pathname.split("/").filter(Boolean);
}

function constantTimeEquals(left, right) {
  if (typeof left !== "string" || typeof right !== "string") {
    return false;
  }

  const leftBytes = new TextEncoder().encode(left);
  const rightBytes = new TextEncoder().encode(right);
  const maxLength = Math.max(leftBytes.length, rightBytes.length);
  let diff = leftBytes.length ^ rightBytes.length;

  for (let index = 0; index < maxLength; index += 1) {
    diff |= (leftBytes[index] ?? 0) ^ (rightBytes[index] ?? 0);
  }

  return diff === 0;
}

function buildOriginRequest(request, env, originPath) {
  const originUrl = new URL(originPath, `${normalizeBaseUrl(env.ORIGIN_BASE_URL)}/`);
  const incomingUrl = new URL(request.url);
  originUrl.search = incomingUrl.search;

  const headers = new Headers(request.headers);
  headers.set("host", originUrl.host);
  headers.set("x-forwarded-host", incomingUrl.host);
  headers.set("x-forwarded-proto", incomingUrl.protocol.replace(":", ""));
  headers.set("x-proxy-by", "cloudflare-worker");

  return new Request(originUrl.toString(), {
    method: request.method,
    headers,
    body: request.method === "GET" || request.method === "HEAD" ? undefined : request.body,
    redirect: "manual",
  });
}

function isStatusRoute(pathname) {
  return pathname === "/health" || pathname === "/status";
}

function resolveWebhookRoute(pathname, env) {
  const parts = splitPath(pathname);

  if (parts.length < 3 || parts[0] !== "webhooks" || parts[1] !== "tradingview") {
    return null;
  }

  const suppliedSecret = parts[2];
  if (!constantTimeEquals(suppliedSecret, env.EDGE_WEBHOOK_SECRET)) {
    return { unauthorized: true };
  }

  const suffix = parts.slice(3).join("/");
  const mappedPath = suffix.length > 0
    ? `/webhooks/tradingview/${env.ORIGIN_WEBHOOK_SECRET}/${suffix}`
    : `/webhooks/tradingview/${env.ORIGIN_WEBHOOK_SECRET}`;

  return { mappedPath };
}

async function proxy(request, env) {
  const url = new URL(request.url);

  if (request.method === "GET" && isStatusRoute(url.pathname)) {
    const originRequest = buildOriginRequest(request, env, url.pathname);
    return fetch(originRequest);
  }

  if (request.method !== "POST") {
    return jsonResponse(
      {
        ok: false,
        error: "Method not allowed",
        allowed_methods: ["POST"],
      },
      405,
    );
  }

  const webhookRoute = resolveWebhookRoute(url.pathname, env);
  if (!webhookRoute) {
    return jsonResponse(
      {
        ok: false,
        error: "Unknown route",
      },
      404,
    );
  }

  if (webhookRoute.unauthorized) {
    return jsonResponse(
      {
        ok: false,
        error: "Unauthorized",
      },
      401,
    );
  }

  const originRequest = buildOriginRequest(request, env, webhookRoute.mappedPath);
  return fetch(originRequest);
}

export default {
  async fetch(request, env, ctx) {
    const startedAt = Date.now();

    try {
      const response = await proxy(request, env);
      ctx.waitUntil(
        Promise.resolve().then(() => {
          console.log(JSON.stringify({
            event: "proxy_request",
            method: request.method,
            path: new URL(request.url).pathname,
            status: response.status,
            duration_ms: Date.now() - startedAt,
          }));
        }),
      );
      return response;
    } catch (error) {
      ctx.waitUntil(
        Promise.resolve().then(() => {
          console.error(JSON.stringify({
            event: "proxy_error",
            message: error instanceof Error ? error.message : "Unknown error",
            path: new URL(request.url).pathname,
            duration_ms: Date.now() - startedAt,
          }));
        }),
      );

      return jsonResponse(
        {
          ok: false,
          error: "Upstream proxy error",
        },
        502,
      );
    }
  },
};
