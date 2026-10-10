import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ListeningLabWorkspace } from "@/components/listening-lab-workspace";

describe("Listening Lab workspace", () => {
  it("states that no browser-playable session is supplied without creating media or capture controls", () => {
    const { container } = render(<ListeningLabWorkspace />);

    expect(screen.getByRole("heading", { name: "Listening Lab" })).toBeInTheDocument();
    expect(screen.getByText(/no authorized browser-playable listening session/i)).toBeInTheDocument();
    expect(screen.getByText(/transcript-only practice cannot complete/i)).toBeInTheDocument();
    expect(container.querySelector("audio")).toBeNull();
    expect(container.querySelector("video")).toBeNull();
    expect(container.querySelector('input[type="file"]')).toBeNull();
    expect(container.querySelector("textarea")).toBeNull();
  });
});
