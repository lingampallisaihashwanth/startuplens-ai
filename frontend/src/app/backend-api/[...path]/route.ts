import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8003").replace(/\/$/, "");

function buildForwardHeaders(req: NextRequest, isJsonBody = false): Record<string, string> {
  const headers: Record<string, string> = {};
  const contentType = req.headers.get("content-type");
  if (contentType) {
    headers["content-type"] = contentType;
  } else if (isJsonBody) {
    headers["content-type"] = "application/json";
  }

  const accept = req.headers.get("accept");
  if (accept) headers["accept"] = accept;

  const cookie = req.headers.get("cookie");
  if (cookie) headers["cookie"] = cookie;

  const auth = req.headers.get("authorization");
  if (auth) headers["authorization"] = auth;

  return headers;
}

function copyResponseHeaders(res: Response): Headers {
  const headers = new Headers();
  const contentType = res.headers.get("content-type") || "application/json";
  headers.set("content-type", contentType);

  const setCookie = res.headers.get("set-cookie");
  if (setCookie) {
    headers.set("set-cookie", setCookie);
  }

  return headers;
}

export async function GET(
  req: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  const { path } = await context.params;
  const targetPath = "/" + (path || []).join("/");
  const url = new URL(targetPath, BACKEND_URL);
  url.search = req.nextUrl.search;

  try {
    const res = await fetch(url.toString(), {
      headers: buildForwardHeaders(req),
    });
    const body = await res.arrayBuffer();
    return new NextResponse(body, {
      status: res.status,
      headers: copyResponseHeaders(res),
    });
  } catch (error) {
    return NextResponse.json(
      { error: { message: "Backend unreachable", detail: String(error) } },
      { status: 502 }
    );
  }
}

export async function POST(
  req: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  const { path } = await context.params;
  const targetPath = "/" + (path || []).join("/");
  const url = new URL(targetPath, BACKEND_URL);
  url.search = req.nextUrl.search;

  try {
    const body = await req.arrayBuffer();
    const res = await fetch(url.toString(), {
      method: "POST",
      headers: buildForwardHeaders(req, body.byteLength > 0),
      body: body.byteLength > 0 ? body : undefined,
    });
    const resBody = await res.arrayBuffer();
    return new NextResponse(resBody, {
      status: res.status,
      headers: copyResponseHeaders(res),
    });
  } catch (error) {
    return NextResponse.json(
      { error: { message: "Backend unreachable", detail: String(error) } },
      { status: 502 }
    );
  }
}

export async function PUT(
  req: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  const { path } = await context.params;
  const targetPath = "/" + (path || []).join("/");
  const url = new URL(targetPath, BACKEND_URL);
  url.search = req.nextUrl.search;

  try {
    const body = await req.arrayBuffer();
    const res = await fetch(url.toString(), {
      method: "PUT",
      headers: buildForwardHeaders(req, body.byteLength > 0),
      body: body.byteLength > 0 ? body : undefined,
    });
    const resBody = await res.arrayBuffer();
    return new NextResponse(resBody, {
      status: res.status,
      headers: copyResponseHeaders(res),
    });
  } catch (error) {
    return NextResponse.json(
      { error: { message: "Backend unreachable", detail: String(error) } },
      { status: 502 }
    );
  }
}

export async function PATCH(
  req: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  const { path } = await context.params;
  const targetPath = "/" + (path || []).join("/");
  const url = new URL(targetPath, BACKEND_URL);
  url.search = req.nextUrl.search;

  try {
    const body = await req.arrayBuffer();
    const res = await fetch(url.toString(), {
      method: "PATCH",
      headers: buildForwardHeaders(req, body.byteLength > 0),
      body: body.byteLength > 0 ? body : undefined,
    });
    const resBody = await res.arrayBuffer();
    return new NextResponse(resBody, {
      status: res.status,
      headers: copyResponseHeaders(res),
    });
  } catch (error) {
    return NextResponse.json(
      { error: { message: "Backend unreachable", detail: String(error) } },
      { status: 502 }
    );
  }
}

export async function DELETE(
  req: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  const { path } = await context.params;
  const targetPath = "/" + (path || []).join("/");
  const url = new URL(targetPath, BACKEND_URL);
  url.search = req.nextUrl.search;

  try {
    const res = await fetch(url.toString(), {
      method: "DELETE",
      headers: buildForwardHeaders(req),
    });
    const resBody = await res.arrayBuffer();
    return new NextResponse(resBody, {
      status: res.status,
      headers: copyResponseHeaders(res),
    });
  } catch (error) {
    return NextResponse.json(
      { error: { message: "Backend unreachable", detail: String(error) } },
      { status: 502 }
    );
  }
}
