import type { components } from "@/api/schema";

export type CaseStatus = components["schemas"]["CaseStatus"];
export type RiskLevel = components["schemas"]["RiskLevel"];
export type FileFormat = components["schemas"]["FileFormat"];
export type FindingCategory = components["schemas"]["FindingCategory"];
export type Severity = components["schemas"]["Severity"];

export type CaseFile = components["schemas"]["CaseFile"];
export type Finding = components["schemas"]["Finding"];
export type Case = components["schemas"]["Case"];
export type TimelineEntry = components["schemas"]["TimelineEntry"];
export type Report = components["schemas"]["Report"];
export type AnalysisProgress = components["schemas"]["AnalysisProgress"];

// UI-only types (not from backend)
export type Tab = "files" | "findings" | "report";
