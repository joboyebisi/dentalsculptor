import { NextRequest, NextResponse } from 'next/server';

// TODO: Use an environment variable for this URL in a real application
const PYTHON_MICROSERVICE_URL = 'http://localhost:8001/convert'; // This will be overridden by Vercel env var in page.tsx, this route itself might not be used if page.tsx calls microservice directly.

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { modelUrl, targetFormat } = body;

    if (!modelUrl || !targetFormat) {
      return NextResponse.json({ error: 'Missing modelUrl or targetFormat' }, { status: 400 });
    }

    if (targetFormat.toLowerCase() !== 'stl' && targetFormat.toLowerCase() !== 'obj') {
      return NextResponse.json({ error: 'Invalid targetFormat. Must be stl or obj.' }, { status: 400 });
    }

    console.log(`API Route (convert-model): Calling Python microservice for ${modelUrl} to ${targetFormat}`);

    // Call the Python microservice
    // NOTE: The page.tsx now calls the Python microservice *directly* using NEXT_PUBLIC_CONVERSION_API_URL.
    // This Next.js API route (src/app/api/convert-model/route.ts) might now be redundant if the frontend
    // calls the Python microservice directly as configured.
    // If this Next.js route IS still intended to be used as a proxy, then PYTHON_MICROSERVICE_URL here
    // should also be an environment variable (e.g., process.env.PYTHON_MICROSERVICE_INTERNAL_URL)
    // set on Vercel for the Next.js project.
    const microserviceResponse = await fetch(PYTHON_MICROSERVICE_URL, { // Or process.env.ACTUAL_MICROSERVICE_URL_FOR_BACKEND
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        glb_url: modelUrl, // Parameter name expected by the Python service
        output_format: targetFormat.toLowerCase(), // Parameter name expected
      }),
    });

    if (!microserviceResponse.ok) {
      let errorBody = 'Conversion microservice failed.';
      try {
        const errJson = await microserviceResponse.json();
        errorBody = errJson.detail || JSON.stringify(errJson);
      } catch (_e) {
        console.warn("Error parsing microservice error response:", _e);
        errorBody = await microserviceResponse.text();
      }
      console.error(`Error from Python microservice (status ${microserviceResponse.status}):`, errorBody);
      return NextResponse.json({ error: `Conversion failed: ${errorBody}` }, { status: microserviceResponse.status });
    }

    const fileData = await microserviceResponse.arrayBuffer();
    const contentType = microserviceResponse.headers.get('content-type') || 'application/octet-stream';
    const contentDisposition = microserviceResponse.headers.get('content-disposition');

    const headers = new Headers();
    headers.set('Content-Type', contentType);
    if (contentDisposition) {
      headers.set('Content-Disposition', contentDisposition);
    }
    headers.set('Content-Length', fileData.byteLength.toString());

    console.log(`API Route (convert-model): Successfully received converted file. Type: ${contentType}, Size: ${fileData.byteLength} bytes. Forwarding to client.`);

    return new NextResponse(fileData, {
      status: 200,
      headers: headers,
    });

  } catch (error) {
    console.error("API Route Error (convert-model) - Outer catch:", error);
    const errorMessage = error instanceof Error ? error.message : 'Internal server error during conversion proxying.';
    return NextResponse.json({ error: errorMessage }, { status: 500 });
  }
}