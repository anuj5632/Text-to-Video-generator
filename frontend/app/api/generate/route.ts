import { type NextRequest, NextResponse } from "next/server"

/**
 * Proxy endpoint to backend /generate
 * This prevents CORS issues and keeps the backend URL private
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { prompt } = body

    if (!prompt || typeof prompt !== "string") {
      return NextResponse.json({ error: "Invalid prompt" }, { status: 400 })
    }

    const API_URL = process.env.BACKEND_API_URL || "http://localhost:8000"

    const response = await fetch(`${API_URL}/generate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ prompt }),
    })

    if (!response.ok) {
      throw new Error("Backend API request failed")
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error("[v0] Generate API error:", error)
    return NextResponse.json({ error: "Failed to start video generation" }, { status: 500 })
  }
}
