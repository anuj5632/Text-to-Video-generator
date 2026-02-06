"use client"

import { useState, ChangeEvent, FormEvent } from "react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Sparkles } from "lucide-react"

interface PromptBoxProps {
  onGenerate: (prompt: string) => void
}

export function PromptBox({ onGenerate }: PromptBoxProps) {
  const [prompt, setPrompt] = useState("")

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    if (prompt.trim()) {
      onGenerate(prompt)
    }
  }

  const handleChange = (e: ChangeEvent<HTMLTextAreaElement>) => {
    setPrompt(e.target.value)
  }

  const examplePrompts = [
    "A serene sunset over the ocean with waves gently crashing",
    "Time-lapse of a bustling city street at night",
    "A coffee cup steaming on a wooden table by a rainy window",
    "Abstract colorful paint swirling in water",
  ]

  return (
    <div className="space-y-6">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="relative">
          <Textarea
            value={prompt}
            onChange={handleChange}
            placeholder="Enter a prompt to generate a video..."
            className="min-h-[160px] text-base resize-none bg-card border-border/50 focus:border-primary/50 transition-colors"
            aria-label="Video generation prompt"
          />
          <div className="absolute bottom-3 right-3 text-xs text-muted-foreground">{prompt.length} characters</div>
        </div>
        <Button type="submit" size="lg" className="w-full text-base font-medium" disabled={!prompt.trim()}>
          <Sparkles className="w-4 h-4 mr-2" />
          Generate Video
        </Button>
      </form>

      {/* Example prompts */}
      <div className="space-y-3">
        <p className="text-sm font-medium text-muted-foreground">Try an example:</p>
        <div className="grid gap-2">
          {examplePrompts.map((example, index) => (
            <button
              key={index}
              onClick={() => setPrompt(example)}
              className="text-left text-sm p-3 rounded-lg border border-border/50 bg-card hover:border-primary/50 hover:bg-accent transition-colors"
            >
              {example}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
