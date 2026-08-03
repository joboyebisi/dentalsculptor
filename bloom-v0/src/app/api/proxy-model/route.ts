import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const modelUrl = searchParams.get('url');

  if (!modelUrl) {
    return NextResponse.json({ error: 'Missing model URL parameter' }, { status: 400 });
  }

  try {
    console.log(`Proxying model request for: ${modelUrl}`);
    // Fetch the model file from the external URL
    const response = await fetch(modelUrl);

    if (!response.ok) {
      throw new Error(`Failed to fetch model: ${response.status} ${response.statusText}`);
    }

    // Get the ArrayBuffer content
    const data = await response.arrayBuffer();
    const contentType = response.headers.get('content-type') || 'application/octet-stream';
    const contentLength = response.headers.get('content-length');

    // Create headers for the proxy response
    const headers = new Headers();
    headers.set('Content-Type', contentType);
    if (contentLength) {
      headers.set('Content-Length', contentLength);
    }
    // You might add caching headers here if desired
    // headers.set('Cache-Control', 'public, max-age=3600'); 

    console.log(`Proxy successful, returning ${contentType} (${data.byteLength} bytes)`);
    // Return the fetched model data directly
    return new NextResponse(data, { status: 200, headers });

  } catch (error) {
    console.error("Proxy API Error:", error);
    const errorMessage = error instanceof Error ? error.message : 'Failed to proxy model request';
    return NextResponse.json({ error: errorMessage }, { status: 502 }); // 502 Bad Gateway indicates proxy failure
  }
} 