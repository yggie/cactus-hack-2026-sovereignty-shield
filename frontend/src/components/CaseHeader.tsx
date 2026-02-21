import type { Case } from "../types";
import { Badge } from "@/components/ui/badge";

interface Props {
  case_: Case;
}

const STATUS_CLASSES: Record<string, string> = {
  open: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  analyzing: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30 animate-pulse",
  complete: "bg-green-500/20 text-green-400 border-green-500/30",
};

const RISK_CLASSES: Record<string, string> = {
  low: "bg-green-500/20 text-green-400 border-green-500/30",
  medium: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  high: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  critical: "bg-red-500/20 text-red-400 border-red-500/30",
};

export default function CaseHeader({ case_ }: Props) {
  return (
    <div className="px-4 py-3 border-b border-border flex items-center gap-3">
      <h2 className="text-lg font-semibold text-foreground">{case_.name}</h2>
      <Badge variant="outline" className={STATUS_CLASSES[case_.status] ?? ""}>
        {case_.status}
      </Badge>
      {case_.status === "complete" && (
        <Badge variant="outline" className={RISK_CLASSES[case_.risk_level] ?? ""}>
          {case_.risk_level} risk
        </Badge>
      )}
    </div>
  );
}
