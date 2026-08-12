import { apiFetchWithAuth, apiUploadWithAuth } from "@/lib/api/client";

export type KnowledgeProcessingStatus = "uploaded" | "processing" | "ready" | "failed";

export type KnowledgeFileListItemDto = {
  id: string;
  bot_id: string;
  original_filename: string;
  mime_type: string;
  file_size_bytes: number;
  processing_status: KnowledgeProcessingStatus;
  processing_error: string | null;
  page_count: number | null;
  uploaded_at: string;
  updated_at: string;
};

export type KnowledgeFileListResponseDto = {
  items: KnowledgeFileListItemDto[];
  total: number;
};

export type KnowledgeFileUploadResponseDto = {
  id: string;
  bot_id: string;
  owner_id: string;
  original_filename: string;
  mime_type: string;
  file_size_bytes: number;
  processing_status: KnowledgeProcessingStatus;
  processing_error: string | null;
  page_count: number | null;
  uploaded_at: string;
  updated_at: string;
};

export async function fetchBotKnowledgeFiles(
  accessToken: string | null,
  botId: string,
): Promise<KnowledgeFileListResponseDto> {
  return apiFetchWithAuth<KnowledgeFileListResponseDto>(`/api/v1/bots/${botId}/knowledge/files`, accessToken, {
    method: "GET",
  });
}

export async function uploadBotKnowledgePdf(
  accessToken: string | null,
  botId: string,
  file: File,
): Promise<KnowledgeFileUploadResponseDto> {
  return apiUploadWithAuth<KnowledgeFileUploadResponseDto>(
    `/api/v1/bots/${botId}/knowledge/files`,
    accessToken,
    file,
    "file",
  );
}
