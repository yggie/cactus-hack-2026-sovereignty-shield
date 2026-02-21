import type { Finding } from "../types";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";

interface Props {
  finding: Finding;
}

const SEVERITY_CLASSES: Record<string, string> = {
  low: "border-green-500/30 bg-green-500/5 text-green-400",
  medium: "border-yellow-500/30 bg-yellow-500/5 text-yellow-400",
  high: "border-orange-500/30 bg-orange-500/5 text-orange-400",
  critical: "border-red-500/30 bg-red-500/5 text-red-400",
};

const CATEGORY_LABELS: Record<string, string> = {
  threat: "Threat",
  scam: "Scam",
  abuse: "Abuse",
  pattern: "Pattern",
  timeline_event: "Event",
  communication: "Communication",
};

export default function FindingCard({ finding }: Props) {
  return (
    <Alert className={SEVERITY_CLASSES[finding.severity] ?? "border-border"}>
      <AlertTitle className="flex items-center gap-2">
        <span className="text-xs font-semibold uppercase">
          {CATEGORY_LABELS[finding.category] ?? finding.category}
        </span>
        <Badge
          variant="outline"
          className={`text-[10px] px-1.5 py-0 h-4 uppercase ${SEVERITY_CLASSES[finding.severity] ?? ""}`}
        >
          {finding.severity}
        </Badge>
        <Badge
          variant="outline"
          className={`ml-auto text-[10px] px-1.5 py-0 h-4 ${
            finding.source === "local"
              ? "bg-green-500/10 text-green-500 border-green-500/30"
              : "bg-amber-500/10 text-amber-500 border-amber-500/30"
          }`}
        >
          {finding.source === "local" ? "on-device" : "cloud"}
        </Badge>
      </AlertTitle>

      <AlertDescription className="space-y-2">
        {finding.quote && (
          <blockquote className="text-sm italic text-muted-foreground border-l-2 border-border pl-2">
            &ldquo;{finding.quote}&rdquo;
          </blockquote>
        )}
        <p className="text-xs text-muted-foreground">{finding.explanation}</p>
      </AlertDescription>
    </Alert>
  );
}
