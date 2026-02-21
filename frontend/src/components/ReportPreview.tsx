import { $api } from "../api/client";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

interface Props {
  caseId: string;
  hasFindings: boolean;
}

export default function ReportPreview({ caseId, hasFindings }: Props) {
  const { data: report, isLoading } = $api.useQuery(
    "get",
    "/api/cases/{case_id}/report",
    { params: { path: { case_id: caseId } } },
    { enabled: hasFindings },
  );

  if (!hasFindings) {
    return (
      <p className="text-sm text-muted-foreground">
        Run analysis first to generate a report.
      </p>
    );
  }

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Generating report...</p>;
  }

  if (!report) return null;

  const handleExport = async () => {
    const res = await fetch(`/api/cases/${caseId}/report/export`);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `report-${caseId}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-muted-foreground">Report Preview</h3>
        <Button variant="secondary" size="sm" onClick={handleExport}>
          Export Markdown
        </Button>
      </div>

      <Card className="p-4 prose prose-invert prose-sm max-w-none">
        <div
          dangerouslySetInnerHTML={{
            __html: markdownToHtml(report.markdown),
          }}
        />
      </Card>
    </div>
  );
}

/** Minimal markdown-to-HTML for report rendering. */
function markdownToHtml(md: string): string {
  return md
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/^### (.+)$/gm, '<h3 class="text-base font-semibold text-foreground mt-4 mb-1">$1</h3>')
    .replace(/^## (.+)$/gm, '<h2 class="text-lg font-bold text-foreground mt-6 mb-2 border-b border-border pb-1">$1</h2>')
    .replace(/^# (.+)$/gm, '<h1 class="text-xl font-bold text-foreground mb-3">$1</h1>')
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/^&gt; (.+)$/gm, '<blockquote class="border-l-2 border-border pl-3 text-muted-foreground italic">$1</blockquote>')
    .replace(/^- (.+)$/gm, '<li class="ml-4 list-disc text-muted-foreground">$1</li>')
    .replace(/^\| (.+) \|$/gm, (_, row: string) => {
      const cells = row.split("|").map((c: string) => c.trim());
      return `<tr>${cells.map((c: string) => `<td class="border border-border px-2 py-1 text-xs">${c}</td>`).join("")}</tr>`;
    })
    .replace(/^---$/gm, '<hr class="border-border my-4" />')
    .replace(/\n/g, "<br/>");
}
