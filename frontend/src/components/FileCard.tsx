import type { CaseFile } from "../types";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface Props {
  file: CaseFile;
}

const FORMAT_LABELS: Record<string, string> = {
  whatsapp: "WhatsApp",
  imessage: "iMessage",
  email: "Email",
  plain_text: "Text",
};

export default function FileCard({ file }: Props) {
  return (
    <Card className="flex-row items-center gap-3 p-3 py-3">
      <div className="w-8 h-8 rounded bg-muted flex items-center justify-center text-xs text-muted-foreground flex-shrink-0">
        {file.filename.split(".").pop()?.toUpperCase() ?? "?"}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-foreground truncate">
          {file.filename}
        </p>
        <div className="flex items-center gap-2 mt-0.5">
          <Badge variant="secondary" className="text-[10px] px-1.5 py-0 h-4">
            {FORMAT_LABELS[file.format] ?? file.format}
          </Badge>
          <span className="text-[10px] text-muted-foreground">
            {file.message_count} messages
          </span>
        </div>
      </div>
      {file.preview && (
        <p className="text-xs text-muted-foreground max-w-48 truncate hidden sm:block">
          {file.preview}
        </p>
      )}
    </Card>
  );
}
