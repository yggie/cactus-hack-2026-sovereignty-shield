import type { Case, Tab, AnalysisProgress } from "../types";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import CaseHeader from "./CaseHeader";
import FileDropZone from "./FileDropZone";
import FileCard from "./FileCard";
import FindingCard from "./FindingCard";
import ReportPreview from "./ReportPreview";
import AnalysisBar from "./AnalysisBar";

interface Props {
  case_: Case;
  activeTab: Tab;
  onTabChange: (tab: Tab) => void;
  onUploadFile: (file: File) => void;
  onAnalyze: () => void;
  onToggleConsent: (consent: boolean) => void;
  progress: AnalysisProgress;
}

export default function CaseWorkspace({
  case_,
  activeTab,
  onTabChange,
  onUploadFile,
  onAnalyze,
  onToggleConsent,
  progress,
}: Props) {
  const files = case_.files ?? [];
  const findings = case_.findings ?? [];

  return (
    <>
      <CaseHeader case_={case_} />

      <Tabs
        value={activeTab}
        onValueChange={(v) => onTabChange(v as Tab)}
        className="flex-1 flex flex-col min-h-0 gap-0"
      >
        <TabsList variant="line" className="px-4 border-b border-border">
          <TabsTrigger value="files">Files</TabsTrigger>
          <TabsTrigger value="findings" className="gap-1.5">
            Findings
            {findings.length > 0 && (
              <Badge variant="secondary" className="text-[10px] px-1.5 py-0 h-4">
                {findings.length}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="report">Report</TabsTrigger>
        </TabsList>

        <TabsContent value="files" className="flex-1 overflow-y-auto p-4">
          <div className="space-y-4">
            <FileDropZone onUpload={onUploadFile} />
            {files.length > 0 && (
              <div className="space-y-2">
                {files.map((f) => (
                  <FileCard key={f.id} file={f} />
                ))}
              </div>
            )}
          </div>
        </TabsContent>

        <TabsContent value="findings" className="flex-1 overflow-y-auto p-4">
          <div className="space-y-3">
            {findings.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No findings yet. Upload files and run analysis.
              </p>
            ) : (
              findings.map((f) => <FindingCard key={f.id} finding={f} />)
            )}
          </div>
        </TabsContent>

        <TabsContent value="report" className="flex-1 overflow-y-auto p-4">
          <ReportPreview caseId={case_.id} hasFindings={findings.length > 0} />
        </TabsContent>
      </Tabs>

      <AnalysisBar
        caseId={case_.id}
        hasFiles={files.length > 0}
        cloudConsent={case_.cloud_consent}
        onToggleConsent={onToggleConsent}
        onAnalyze={onAnalyze}
        progress={progress}
      />
    </>
  );
}
