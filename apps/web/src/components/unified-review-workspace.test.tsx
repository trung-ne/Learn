import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { UnifiedReviewWorkspace } from "@/components/unified-review-workspace";

describe("UnifiedReviewWorkspace", () => {
  it("uses a local, non-diagnostic empty state", async () => {
    render(<UnifiedReviewWorkspace language="en" course="A1" />);
    expect(await screen.findByText(/No locally scheduled review is ready/i)).toBeInTheDocument();
    expect(screen.getByText(/not a learning diagnosis, proficiency result, or placement decision/i)).toBeInTheDocument();
    expect(screen.queryByText(/weak grammar/i)).not.toBeInTheDocument();
  });
});
