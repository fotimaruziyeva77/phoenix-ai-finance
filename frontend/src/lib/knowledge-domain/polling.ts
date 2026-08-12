import type { KnowledgeProcessingStatus } from "@/lib/api/bot-knowledge";

/** True while any file is still in the async PDF pipeline (list should refresh periodically). */
export function knowledgeFilesNeedPolling(processingStatus: KnowledgeProcessingStatus): boolean {
  return processingStatus === "uploaded" || processingStatus === "processing";
}

export function knowledgeListNeedsPolling(items: { processing_status: KnowledgeProcessingStatus }[]): boolean {
  return items.some((i) => knowledgeFilesNeedPolling(i.processing_status));
}
