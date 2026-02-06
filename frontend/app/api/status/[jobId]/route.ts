import { type NextRequest, NextResponse } from "next/server"

/**
 * Proxy endpoint to check job status
 * This endpoint assumes the backend has a status endpoint
 */
export async function GET(request: NextRequest, { params }: { params: Promise<{ jobId: string }> }) {
  try {
    const { jobId } = await params

    if (!jobId) {
      return NextResponse.json({ error: "Job ID is required" }, { status: 400 })
    }

    const API_URL = process.env.BACKEND_API_URL || "http://localhost:8000"

    const response = await fetch(`${API_URL}/status/${jobId}`)

    if (!response.ok) {
      throw new Error("Failed to fetch job status")
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error("[v0] Status API error:", error)
    return NextResponse.json({ error: "Failed to check job status" }, { status: 500 })
  }
}
