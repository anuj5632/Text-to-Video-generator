"use client"

import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Download, RotateCcw } from "lucide-react"

interface VideoPlayerProps {
  videoUrl: string
  onReset: () => void
}

export function VideoPlayer({ videoUrl, onReset }: VideoPlayerProps) {
  const handleDownload = () => {
    const link = document.createElement("a")
    link.href = videoUrl
    link.download = `generated-video-${Date.now()}.mp4`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  return (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <h2 className="text-2xl md:text-3xl font-bold text-foreground">Your Video is Ready! 🎉</h2>
        <p className="text-muted-foreground">Preview your generated video below</p>
      </div>

      <Card className="border-border/50 overflow-hidden">
        <CardContent className="p-0">
          {/* Video player */}
          <div className="aspect-video bg-black">
            <video controls className="w-full h-full" src={videoUrl} aria-label="Generated video">
              Your browser does not support the video tag.
            </video>
          </div>

          {/* Actions */}
          <div className="p-6 space-y-4">
            <div className="flex flex-col sm:flex-row gap-3">
              <Button onClick={handleDownload} size="lg" className="flex-1">
                <Download className="w-4 h-4 mr-2" />
                Download Video
              </Button>
              <Button onClick={onReset} size="lg" variant="outline" className="flex-1 bg-transparent">
                <RotateCcw className="w-4 h-4 mr-2" />
                Generate Another Video
              </Button>
            </div>

            <p className="text-xs text-center text-muted-foreground">
              Video will be available for download for 24 hours
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
