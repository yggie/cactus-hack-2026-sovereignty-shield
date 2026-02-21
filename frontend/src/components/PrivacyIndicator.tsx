import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip";

interface Props {
  cloudConsent: boolean;
}

export default function PrivacyIndicator({ cloudConsent }: Props) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Badge
          variant="outline"
          className={`cursor-default gap-2 ${
            cloudConsent
              ? "bg-amber-500/10 text-amber-400 border-amber-500/30"
              : "bg-green-500/10 text-green-400 border-green-500/30"
          }`}
        >
          <div
            className={`w-2 h-2 rounded-full ${
              cloudConsent ? "bg-amber-400" : "bg-green-400"
            }`}
          />
          {cloudConsent ? "CLOUD ENABLED" : "ALL LOCAL"}
        </Badge>
      </TooltipTrigger>
      <TooltipContent>
        {cloudConsent
          ? "Data may be sent to Gemini when confidence is low"
          : "All analysis runs on-device via FunctionGemma"}
      </TooltipContent>
    </Tooltip>
  );
}
