import type { AnalysisProgress } from "../types";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Progress } from "@/components/ui/progress";

interface Props {
  caseId: string;
  hasFiles: boolean;
  cloudConsent: boolean;
  onToggleConsent: (consent: boolean) => void;
  onAnalyze: () => void;
  progress: AnalysisProgress;
}

export default function AnalysisBar({
  hasFiles,
  cloudConsent,
  onToggleConsent,
  onAnalyze,
  progress,
}: Props) {
  const isAnalyzing = progress.status === "analyzing";
  const pct =
    progress.total > 0
      ? Math.round((progress.completed / progress.total) * 100)
      : 0;

  return (
    <div className="border-t border-border px-4 py-3 flex items-center gap-4 bg-card/50">
      {/* Cloud consent toggle */}
      <label className="flex items-center gap-2 cursor-pointer select-none">
        <Switch
          checked={cloudConsent}
          onCheckedChange={onToggleConsent}
          className="data-[state=checked]:bg-amber-600"
          size="sm"
        />
        <span className="text-xs text-muted-foreground">
          {cloudConsent ? "Cloud fallback ON" : "Local only"}
        </span>
      </label>

      {/* Progress */}
      {isAnalyzing ? (
        <div className="flex-1 flex items-center gap-2">
          <Progress value={pct} className="flex-1 h-1.5" />
          <span className="text-xs text-muted-foreground tabular-nums">
            {progress.completed}/{progress.total}
          </span>
        </div>
      ) : (
        <div className="flex-1" />
      )}

      {/* Analyze button */}
      <Button
        onClick={onAnalyze}
        disabled={!hasFiles || isAnalyzing}
        size="sm"
      >
        {isAnalyzing ? "Analyzing..." : "Analyze"}
      </Button>
    </div>
  );
}
