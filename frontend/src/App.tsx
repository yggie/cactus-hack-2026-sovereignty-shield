import { useState, useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { $api } from "./api/client";
import type { Tab } from "./types";
import CaseSidebar from "./components/CaseSidebar";
import CaseWorkspace from "./components/CaseWorkspace";
import EmptyState from "./components/EmptyState";

function App() {
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("files");
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  // List cases
  const { data: cases = [] } = $api.useQuery("get", "/api/cases");

  const selectedCase = cases.find((c) => c.id === selectedId) ?? null;

  // Poll progress while analyzing
  const { data: progress } = $api.useQuery(
    "get",
    "/api/cases/{case_id}/progress",
    { params: { path: { case_id: selectedId! } } },
    {
      enabled: !!selectedId && isAnalyzing,
      refetchInterval: 500,
    },
  );

  const progressData = progress ?? { total: 0, completed: 0, status: "idle" };

  // Stop polling when analysis completes
  useEffect(() => {
    if (isAnalyzing && progress?.status === "complete") {
      setIsAnalyzing(false);
      queryClient.invalidateQueries({ queryKey: ["get", "/api/cases"] });
      setActiveTab("findings");
    }
  }, [isAnalyzing, progress?.status, queryClient]);

  // Reset analyzing state when switching cases
  useEffect(() => {
    setIsAnalyzing(false);
  }, [selectedId]);

  // Mutations
  const createCase = $api.useMutation("post", "/api/cases", {
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["get", "/api/cases"] });
      setSelectedId(data.id);
      setActiveTab("files");
    },
  });

  const deleteCase = $api.useMutation("delete", "/api/cases/{case_id}", {
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["get", "/api/cases"] });
    },
  });

  const updateCase = $api.useMutation("patch", "/api/cases/{case_id}", {
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["get", "/api/cases"] });
    },
  });

  const analyzeMutation = $api.useMutation(
    "post",
    "/api/cases/{case_id}/analyze",
    {
      onSuccess: () => {
        setIsAnalyzing(true);
      },
    },
  );

  const handleDeleteCase = (caseId: string) => {
    if (selectedId === caseId) setSelectedId(null);
    deleteCase.mutate({ params: { path: { case_id: caseId } } });
  };

  // File upload stays as raw fetch (multipart)
  const handleUploadFile = async (file: File) => {
    if (!selectedId) return;
    const form = new FormData();
    form.append("file", file);
    await fetch(`/api/cases/${selectedId}/files`, {
      method: "POST",
      body: form,
    });
    queryClient.invalidateQueries({ queryKey: ["get", "/api/cases"] });
  };

  return (
    <div className="flex h-screen bg-background text-foreground">
      <CaseSidebar
        cases={cases}
        selectedId={selectedId}
        onSelect={setSelectedId}
        onCreate={(name) => createCase.mutate({ body: { name } })}
        onDelete={handleDeleteCase}
        cloudConsent={selectedCase?.cloud_consent ?? false}
      />
      <div className="flex-1 flex flex-col min-w-0">
        {selectedCase ? (
          <CaseWorkspace
            case_={selectedCase}
            activeTab={activeTab}
            onTabChange={setActiveTab}
            onUploadFile={handleUploadFile}
            onAnalyze={() =>
              analyzeMutation.mutate({
                params: { path: { case_id: selectedId! } },
              })
            }
            onToggleConsent={(consent) =>
              updateCase.mutate({
                params: { path: { case_id: selectedId! } },
                body: { cloud_consent: consent },
              })
            }
            progress={progressData}
          />
        ) : (
          <EmptyState />
        )}
      </div>
    </div>
  );
}

export default App;
