import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8003").replace(/\/$/, "");

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
      headers: {
        Accept: req.headers.get("accept") || "application/json",
      },
    });
    const body = await res.arrayBuffer();
    return new NextResponse(body, {
      status: res.status,
      headers: {
        "content-type": res.headers.get("content-type") || "application/json",
      },
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
    const headers: Record<string, string> = {};
    const contentType = req.headers.get("content-type");
    if (contentType) headers["content-type"] = contentType;

    const res = await fetch(url.toString(), {
      method: "POST",
      headers,
      body: body.byteLength > 0 ? body : undefined,
    });
    const resBody = await res.arrayBuffer();
    return new NextResponse(resBody, {
      status: res.status,
      headers: {
        "content-type": res.headers.get("content-type") || "application/json",
      },
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
    const headers: Record<string, string> = {};
    const contentType = req.headers.get("content-type");
    if (contentType) headers["content-type"] = contentType;

    const res = await fetch(url.toString(), {
      method: "PUT",
      headers,
      body: body.byteLength > 0 ? body : undefined,
    });
    const resBody = await res.arrayBuffer();
    return new NextResponse(resBody, {
      status: res.status,
      headers: {
        "content-type": res.headers.get("content-type") || "application/json",
      },
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
    const headers: Record<string, string> = {};
    const contentType = req.headers.get("content-type");
    if (contentType) headers["content-type"] = contentType;

    const res = await fetch(url.toString(), {
      method: "PATCH",
      headers,
      body: body.byteLength > 0 ? body : undefined,
    });
    const resBody = await res.arrayBuffer();
    return new NextResponse(resBody, {
      status: res.status,
      headers: {
        "content-type": res.headers.get("content-type") || "application/json",
      },
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
    });
    const resBody = await res.arrayBuffer();
    return new NextResponse(resBody, {
      status: res.status,
      headers: {
        "content-type": res.headers.get("content-type") || "application/json",
      },
    });
  } catch (error) {
    return NextResponse.json(
      { error: { message: "Backend unreachable", detail: String(error) } },
      { status: 502 }
    );
  }
}
