import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { KnowledgeUploadZone } from "./knowledge-upload-zone";

describe("KnowledgeUploadZone", () => {
  it("renders upload affordance and PDF-only hint", () => {
    const onFile = vi.fn();
    render(
      <KnowledgeUploadZone onFileSelected={onFile} errorMessage={null} onDismissError={vi.fn()} />,
    );
    expect(screen.getByLabelText(/Upload PDF knowledge file/i)).toBeInTheDocument();
    expect(screen.getByText(/Drop a PDF here or click to browse/i)).toBeInTheDocument();
    expect(screen.getByText(/PDF only/i)).toBeInTheDocument();
  });

  it("shows upload error from parent without inventing success state", () => {
    render(
      <KnowledgeUploadZone
        onFileSelected={vi.fn()}
        errorMessage="Only PDF files are allowed."
        onDismissError={vi.fn()}
      />,
    );
    expect(screen.getByTestId("knowledge-upload-error")).toHaveTextContent("Only PDF files are allowed.");
  });

  it("invokes onFileSelected with the chosen file", async () => {
    const user = userEvent.setup();
    const onFile = vi.fn();
    render(<KnowledgeUploadZone onFileSelected={onFile} errorMessage={null} onDismissError={vi.fn()} />);
    const file = new File(["%PDF-1.4"], "test.pdf", { type: "application/pdf" });
    const input = screen.getByLabelText(/Upload PDF knowledge file/i);
    await user.upload(input, file);
    expect(onFile).toHaveBeenCalledTimes(1);
    expect(onFile.mock.calls[0][0]).toBe(file);
  });
});
