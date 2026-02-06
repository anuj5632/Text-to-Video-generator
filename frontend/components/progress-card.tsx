"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Loader2, Copy, Check } from "lucide-react"

interface ProgressCardProps {
  jobId: string
  progress?: number
  stage?: string
  message?: string
}

// Map backend stages to user-friendly messages
const stageMessages: Record<string, string> = {
  START: "Initializing...",
  INIT: "Setting up generation...",
  SCRIPT: "Generating script...",
  VOICEOVER: "Creating voiceover...",
  IMAGE_PREP: "Preparing image prompts...",
  IMAGE_GEN: "Generating images...",
  VIDEO: "Assembling video...",
  CAPTIONS: "Adding captions...",
  CLEANUP: "Finalizing...",
  DONE: "Video ready!",
  ERROR: "An error occurred",
}

export function ProgressCard({ jobId, progress = 0, stage = "", message = "" }: ProgressCardProps) {
  const [copied, setCopied] = useState(false)

  const displayMessage = stageMessages[stage] || message || "Processing..."

  const handleCopy = () => {
    navigator.clipboard.writeText(jobId)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="space-y-6">
      <Card className="border-border/50">
        <CardHeader>
          <CardTitle className="flex items-center gap-3">
            <Loader2 className="w-5 h-5 animate-spin text-primary" />
            Generating Your Video
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Progress indicator */}
          <div className="space-y-3">
            <div className="flex items-center justify-between text-sm">
              <span className="text-foreground font-medium">{displayMessage}</span>
              <span className="text-muted-foreground">{progress}% complete</span>
            </div>
            <div className="h-2 bg-secondary rounded-full overflow-hidden">
              <div
                className="h-full bg-primary transition-all duration-500 ease-out rounded-full"
                style={{ width: `${Math.max(progress, 5)}%` }}
              />
            </div>
            {message && stage && (
              <p className="text-xs text-muted-foreground">{message}</p>
            )}
          </div>

          {/* Job ID */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-muted-foreground">Job ID</label>
            <div className="flex items-center gap-2">
              <code className="flex-1 px-3 py-2 bg-muted rounded-md text-sm font-mono text-foreground">{jobId}</code>
              <Button variant="outline" size="icon" onClick={handleCopy} aria-label="Copy job ID">
                {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">Save this ID to check your video status later</p>
          </div>

          {/* Info message */}
          <div className="p-4 bg-primary/5 border border-primary/20 rounded-lg">
            <p className="text-sm text-foreground">
              <span className="font-medium">Tip:</span> You can close this page. Your video will continue generating in
              the background.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
