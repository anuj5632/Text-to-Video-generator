"use client"

import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { AlertCircle, RotateCcw } from "lucide-react"

interface ErrorStateProps {
  error: string
  onRetry: () => void
}

export function ErrorState({ error, onRetry }: ErrorStateProps) {
  return (
    <div className="space-y-6">
      <Card className="border-destructive/50">
        <CardContent className="pt-6">
          <div className="flex flex-col items-center text-center space-y-4">
            <div className="w-12 h-12 rounded-full bg-destructive/10 flex items-center justify-center">
              <AlertCircle className="w-6 h-6 text-destructive" />
            </div>
            <div className="space-y-2">
              <h3 className="text-xl font-semibold text-foreground">Something went wrong</h3>
              <p className="text-muted-foreground max-w-md">
                {error || "An unexpected error occurred while generating your video."}
              </p>
            </div>
            <Button onClick={onRetry} size="lg">
              <RotateCcw className="w-4 h-4 mr-2" />
              Try Again
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Troubleshooting tips */}
      <Card className="border-border/50">
        <CardContent className="pt-6">
          <h4 className="font-medium text-foreground mb-3">Troubleshooting tips:</h4>
          <ul className="space-y-2 text-sm text-muted-foreground list-disc list-inside">
            <li>Make sure your prompt is clear and descriptive</li>
            <li>Check your internet connection</li>
            <li>Try a shorter or simpler prompt</li>
            <li>Contact support if the issue persists</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  )
}
