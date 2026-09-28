import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import LessonNotFound from "./not-found";

describe("lesson not found page", () => {
  it("offers a learner-safe way back to available courses", () => {
    render(<LessonNotFound />);
    expect(screen.getByRole("heading", { name: "This lesson is not in the current course." })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Browse available courses" })).toHaveAttribute("href", "/learn");
  });
});
