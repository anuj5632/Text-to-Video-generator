"use client"

import { useState } from "react"
import { PromptBox } from "@/components/prompt-box"
import { ProgressCard } from "@/components/progress-card"
import { VideoPlayer } from "@/components/video-player"
import { ErrorState } from "@/components/error-state"
import { Sparkles } from "lucide-react"

type AppState = "idle" | "generating" | "success" | "error"

const API_BASE = "http://127.0.0.1:8000"

interface ProgressData {
  progress: number
  stage: string
  message: string
}

export default function Home() {
  const [state, setState] = useState<AppState>("idle")
  const [jobId, setJobId] = useState<string>("")
  const [videoUrl, setVideoUrl] = useState<string>("")
  const [error, setError] = useState<string>("")
  const [progressData, setProgressData] = useState<ProgressData>({
    progress: 0,
    stage: "",
    message: ""
  })

  const handleGenerate = async (prompt: string) => {
    try {
      setState("generating")
      setError("")
      setProgressData({ progress: 0, stage: "START", message: "Starting..." })

      // 1️⃣ Start video generation
      const response = await fetch(`${API_BASE}/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      })

      if (!response.ok) {
        throw new Error("Failed to start video generation")
      }

      const data = await response.json()
      setJobId(data.job_id)

      // 2️⃣ Poll job status
      pollJobStatus(data.job_id)
    } catch (err) {
      setState("error")
      setError(err instanceof Error ? err.message : "An unexpected error occurred")
    }
  }

  const pollJobStatus = (id: string) => {
    const maxAttempts = 600 // ~30 minutes at 3 second intervals
    let attempts = 0

    const poll = setInterval(async () => {
      try {
        const response = await fetch(`${API_BASE}/status/${id}`)

        if (!response.ok) {
          throw new Error("Failed to fetch job status")
        }

        const data = await response.json()

        // Update progress data for the UI
        setProgressData({
          progress: data.progress || 0,
          stage: data.stage || "",
          message: data.message || ""
        })

        if (data.state === "completed") {
          clearInterval(poll)
          setVideoUrl(data.video_url)
          setState("success")
        } else if (data.state === "failed") {
          clearInterval(poll)
          setState("error")
          setError(data.message || "Video generation failed")
        } else if (data.state === "not_found" && attempts > 10) {
          // Give some time for the job to be created
          clearInterval(poll)
          setState("error")
          setError("Job not found. Please try again.")
        }

        attempts++
        if (attempts >= maxAttempts) {
          clearInterval(poll)
          setState("error")
          setError("Video generation timed out")
        }
      } catch (err) {
        // Don't fail immediately on network errors, keep trying
        console.error("Polling error:", err)
        attempts++
        if (attempts >= maxAttempts) {
          clearInterval(poll)
          setState("error")
          setError(err instanceof Error ? err.message : "Failed to check status")
        }
      }
    }, 3000) // Poll every 3 seconds
  }

  const handleReset = () => {
    setState("idle")
    setJobId("")
    setVideoUrl("")
    setError("")
    setProgressData({ progress: 0, stage: "", message: "" })
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border/50">
        <div className="container mx-auto px-4 py-6">
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-primary/10 text-primary">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-xl font-semibold text-foreground">
                Text to Video Generator
              </h1>
              <p className="text-sm text-muted-foreground">
                Transform your ideas into stunning videos
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-12 max-w-4xl">
        {state === "idle" && (
          <div className="space-y-8">
            <div className="text-center space-y-4 mb-12">
              <h2 className="text-4xl md:text-5xl font-bold text-foreground">
                Create videos from text
              </h2>
              <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                Describe your vision and our AI will generate a professional
                video in minutes.
              </p>
            </div>
            <PromptBox onGenerate={handleGenerate} />
          </div>
        )}

        {state === "generating" && (
          <ProgressCard 
            jobId={jobId} 
            progress={progressData.progress}
            stage={progressData.stage}
            message={progressData.message}
          />
        )}

        {state === "success" && (
          <VideoPlayer videoUrl={videoUrl} onReset={handleReset} />
        )}

        {state === "error" && (
          <ErrorState error={error} onRetry={handleReset} />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-border/50 mt-20">
        <div className="container mx-auto px-4 py-8">
          <p className="text-center text-sm text-muted-foreground">
            Powered by AI • Generation time: 3–8 minutes
          </p>
        </div>
      </footer>
    </div>
  )
}
