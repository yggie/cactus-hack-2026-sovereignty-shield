import { Card, CardContent } from "@/components/ui/card";

export default function EmptyState() {
  return (
    <div className="flex-1 flex items-center justify-center">
      <Card className="max-w-sm text-center border-none shadow-none bg-transparent">
        <CardContent className="space-y-2">
          <div className="text-4xl mb-1 opacity-30">&#128274;</div>
          <h2 className="text-lg font-semibold text-foreground">
            Confidential Document Analyst
          </h2>
          <p className="text-sm text-muted-foreground">
            Create a case and upload sensitive documents for local-first AI
            analysis. Identify threats, scams, abuse patterns, and build
            structured reports for legal review.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
