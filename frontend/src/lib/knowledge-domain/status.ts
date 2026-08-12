export type KnowledgeProcessingStatus = "uploaded" | "processing" | "ready" | "failed";

export type KnowledgeStatusVariant = "queued" | "progress" | "ready" | "failed";

export function knowledgeStatusVariant(status: KnowledgeProcessingStatus): KnowledgeStatusVariant {
  switch (status) {
    case "uploaded":
      return "queued";
    case "processing":
      return "progress";
    case "ready":
      return "ready";
    case "failed":
      return "failed";
    default:
      return "queued";
  }
}

/** Short label for chips and tables. */
export function knowledgeStatusLabel(status: KnowledgeProcessingStatus): string {
  switch (status) {
    case "uploaded":
      return "Queued";
    case "processing":
      return "Processing";
    case "ready":
      return "Ready";
    case "failed":
      return "Failed";
    default:
      return status;
  }
}

/** One-line explanation for tooltips and empty states. */
export function knowledgeStatusDescription(status: KnowledgeProcessingStatus): string {
  switch (status) {
    case "uploaded":
      return "Waiting to start text extraction.";
    case "processing":
      return "Extracting text and indexing for search.";
    case "ready":
      return "Available to your bot during conversations.";
    case "failed":
      return "Could not process this file. See the error message below.";
    default:
      return "";
  }
}
