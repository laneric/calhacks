import { NextRequest } from 'next/server';

// flask backend url
const FLASK_API_URL = 'http://localhost:5001';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const lat = parseFloat(searchParams.get('lat') || '');
    const lng = parseFloat(searchParams.get('lng') || '');
    const radius = parseInt(searchParams.get('radius') || '5000'); // default 5km
    const researchLimit = parseInt(searchParams.get('researchLimit') || '3'); // default research 3 restaurants

    // validate parameters
    if (isNaN(lat) || isNaN(lng)) {
      return new Response(
        JSON.stringify({ error: 'Invalid latitude or longitude parameters' }),
        {
          status: 400,
          headers: { 'Content-Type': 'application/json' }
        }
      );
    }

    if (radius < 100 || radius > 50000) {
      return new Response(
        JSON.stringify({ error: 'Radius must be between 100m and 50km' }),
        {
          status: 400,
          headers: { 'Content-Type': 'application/json' }
        }
      );
    }

    // call flask backend streaming endpoint
    const flaskUrl = `${FLASK_API_URL}/restaurants/research/stream?lat=${lat}&lng=${lng}&radius=${radius}&limit=${researchLimit}`;

    console.log('Calling Flask streaming API:', flaskUrl);

    const flaskResponse = await fetch(flaskUrl, {
      method: 'GET',
      headers: {
        'Accept': 'text/event-stream',
      },
    });

    if (!flaskResponse.ok) {
      return new Response(
        JSON.stringify({ error: 'Flask API error' }),
        {
          status: flaskResponse.status,
          headers: { 'Content-Type': 'application/json' }
        }
      );
    }

    // proxy the stream from flask to the client
    const stream = new ReadableStream({
      async start(controller) {
        const reader = flaskResponse.body?.getReader();
        if (!reader) {
          controller.close();
          return;
        }

        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            controller.enqueue(value);
          }
        } catch (error) {
          console.error('Stream error:', error);
          controller.error(error);
        } finally {
          controller.close();
        }
      },
    });

    return new Response(stream, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      },
    });

  } catch (error) {
    console.error('Restaurant streaming API error:', error);
    return new Response(
      JSON.stringify({ error: 'Internal server error', details: String(error) }),
      {
        status: 500,
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }
}
