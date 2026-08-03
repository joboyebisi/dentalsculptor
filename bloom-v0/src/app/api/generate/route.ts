import { NextRequest, NextResponse } from 'next/server';
import { fal } from "@fal-ai/client"; // Import fal client

// Ensure FAL_KEY is set in environment variables
if (!process.env.FAL_KEY) {
  throw new Error("FAL_KEY environment variable not set.");
}

// Optional: Configure fal client if needed (using env var is preferred)
// fal.config({
//   credentials: process.env.FAL_KEY,
// });

// Define expected output structure WITHIN the result.data field
interface FalOutputData {
  model_mesh: {
    url: string;
    content_type: string;
    file_name: string;
    file_size: number;
  };
  seed: number;
}

// Removed FalSubscribeResult interface as it caused type constraint issues
// interface FalSubscribeResult { ... }

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const files = formData.getAll('files') as File[];

    if (!files || files.length === 0) {
      return NextResponse.json({ error: 'No files uploaded.' }, { status: 400 });
    }

    const imageFile = files[0]; // Use the first uploaded file
    console.log(`API Route: Processing file: ${imageFile.name}`);

    // 1. Upload the image file to Fal Storage
    console.log("API Route: Uploading image to Fal Storage...");
    const imageUrl = await fal.storage.upload(imageFile);
    console.log(`API Route: Image uploaded, URL: ${imageUrl}`);

    // 2. Call the Fal AI model using fal.subscribe (simpler for direct result)
    console.log("API Route: Calling Fal AI model...");
    // Assign to unknown first, then cast where needed
    const result: unknown = await fal.subscribe("fal-ai/hunyuan3d/v2/turbo", {
      input: {
        input_image_url: imageUrl,
        // Add any other parameters from the schema if needed
        // e.g., num_inference_steps: 50, guidance_scale: 7.5
      },
      logs: true, // Enable logs for debugging
      onQueueUpdate: (update) => {
        // Optional: Log progress updates from Fal AI
        if (update.status === "IN_PROGRESS") {
          update.logs?.map((log) => log.message).forEach(msg => console.log("Fal AI Log:", msg));
        }
      },
    });

    // 3. Extract the model URL from the result.data
    // Type assertion when accessing nested properties
    const output = (result as { data: FalOutputData })?.data;

    if (!output?.model_mesh?.url) {
        console.error("API Route Error: Fal AI response data missing model_mesh.url", result); // Log the full result for debugging
        throw new Error("Failed to get model URL from Fal AI response.");
    }
    const modelUrl = output.model_mesh.url;
    console.log(`API Route: Fal AI Generation successful. Model URL: ${modelUrl}`);

    // 4. Return the model URL to the frontend
    return NextResponse.json({ modelUrl: modelUrl }, { status: 200 });

  } catch (error) {
    console.error("API Route Error:", error);
    const errorMessage = error instanceof Error ? error.message : 'Internal server error processing request.';
    return NextResponse.json({ error: errorMessage }, { status: 500 });
  }
} 