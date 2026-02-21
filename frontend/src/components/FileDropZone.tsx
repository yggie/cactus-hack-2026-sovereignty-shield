import { useState, useCallback } from "react";
import { Button } from "@/components/ui/button";

interface Props {
  onUpload: (file: File) => void;
}

export default function FileDropZone({ onUpload }: Props) {
  const [dragging, setDragging] = useState(false);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const files = Array.from(e.dataTransfer.files);
      files.forEach(onUpload);
    },
    [onUpload]
  );

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    files.forEach(onUpload);
    e.target.value = "";
  };

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
        dragging
          ? "border-primary bg-primary/10"
          : "border-border hover:border-muted-foreground"
      }`}
    >
      <p className="text-sm text-muted-foreground">
        Drag & drop files here, or{" "}
        <Button variant="link" size="sm" className="h-auto p-0" asChild>
          <label className="cursor-pointer">
            browse
            <input
              type="file"
              className="hidden"
              multiple
              accept=".txt,.eml,.csv,.log"
              onChange={handleFileInput}
            />
          </label>
        </Button>
      </p>
      <p className="text-xs text-muted-foreground/60 mt-1">
        Supports WhatsApp exports, emails (.eml), iMessage, and plain text
      </p>
    </div>
  );
}
