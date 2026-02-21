import { useState } from "react";
import type { Case } from "../types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import PrivacyIndicator from "./PrivacyIndicator";

interface Props {
  cases: Case[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onCreate: (name: string) => void;
  onDelete: (id: string) => void;
  cloudConsent: boolean;
}

const STATUS_VARIANT: Record<string, string> = {
  open: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  analyzing: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  complete: "bg-green-500/20 text-green-400 border-green-500/30",
};

export default function CaseSidebar({
  cases,
  selectedId,
  onSelect,
  onCreate,
  onDelete,
  cloudConsent,
}: Props) {
  const [newName, setNewName] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const name = newName.trim();
    if (!name) return;
    onCreate(name);
    setNewName("");
  };

  return (
    <div className="w-60 flex-shrink-0 flex flex-col border-r border-border bg-card/50">
      <div className="p-3 border-b border-border">
        <h1 className="text-sm font-semibold text-muted-foreground tracking-wide uppercase">
          Cases
        </h1>
        <form onSubmit={handleSubmit} className="mt-2 flex gap-1">
          <Input
            type="text"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="New case name..."
            className="flex-1 h-7 text-sm"
          />
          <Button type="submit" size="xs">
            +
          </Button>
        </form>
      </div>

      <ScrollArea className="flex-1">
        {cases.map((c) => (
          <div
            key={c.id}
            onClick={() => onSelect(c.id)}
            className={`group px-3 py-2 cursor-pointer border-b border-border/50 transition-colors ${
              c.id === selectedId
                ? "bg-primary/10 border-l-2 border-l-primary"
                : "hover:bg-accent/50 border-l-2 border-l-transparent"
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-foreground truncate">
                {c.name}
              </span>
              <Button
                variant="ghost"
                size="icon-xs"
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(c.id);
                }}
                className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-destructive"
              >
                ×
              </Button>
            </div>
            <div className="flex items-center gap-2 mt-1">
              <Badge
                variant="outline"
                className={`text-[10px] px-1.5 py-0 ${STATUS_VARIANT[c.status] ?? ""}`}
              >
                {c.status}
              </Badge>
              <span className="text-[10px] text-muted-foreground">
                {c.files?.length ?? 0} files
              </span>
            </div>
          </div>
        ))}
        {cases.length === 0 && (
          <p className="text-xs text-muted-foreground p-3">No cases yet</p>
        )}
      </ScrollArea>

      <div className="p-3 border-t border-border">
        <PrivacyIndicator cloudConsent={cloudConsent} />
      </div>
    </div>
  );
}
