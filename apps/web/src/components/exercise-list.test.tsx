import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { ExerciseList } from "@/components/exercise-list";
import type { DisplayExercise } from "@/content/types";
import type { ExerciseRunnerState } from "@/lib/progress";

const exercises: readonly DisplayExercise[] = [
  {
    id: "choose-greeting",
    type: "multiple_choice",
    prompt: "Choose a greeting.",
    options: ["Hello", "Yesterday"],
    correct_answer: "Hello",
  },
  {
    id: "say-hello",
    type: "speaking",
    prompt: "Say hello to a classmate.",
    rubric: { criteria: ["Use a greeting."] },
  },
];

function ExerciseHarness({
  onCheck = () => {},
}: {
  readonly onCheck?: (exerciseId: string, result: "correct" | "incorrect") => void;
}) {
  const [runner, setRunner] = useState<ExerciseRunnerState>({
    currentExerciseId: exercises[0]!.id,
    finished: false,
    exercises: {},
  });
  return (
    <ExerciseList
      exercises={exercises}
      runner={runner}
      onCheck={(exerciseId, result) => {
        onCheck(exerciseId, result);
        setRunner((current) => ({
          ...current,
          exercises: {
            ...current.exercises,
            [exerciseId]: { lastResult: result, completed: result === "correct" },
          },
        }));
      }}
      onAdvance={(nextExerciseId) =>
        setRunner((current) => ({
          ...current,
          currentExerciseId: nextExerciseId,
          finished: !nextExerciseId,
        }))
      }
      onSelfPractice={(exerciseId, nextExerciseId) =>
        setRunner((current) => ({
          ...current,
          currentExerciseId: nextExerciseId,
          finished: !nextExerciseId,
          exercises: {
            ...current.exercises,
            [exerciseId]: { lastResult: "self_practice", completed: true },
          },
        }))
      }
      onRestart={() =>
        setRunner({ currentExerciseId: exercises[0]!.id, finished: false, exercises: {} })
      }
    />
  );
}

describe("ExerciseList", () => {
  it("explains when a lesson has no supplied exercises", () => {
    render(
      <ExerciseList
        exercises={[]}
        onCheck={() => {}}
        onAdvance={() => {}}
        onSelfPractice={() => {}}
        onRestart={() => {}}
      />,
    );

    expect(
      screen.getByText("No exercises are available for this lesson yet."),
    ).toBeInTheDocument();
  });

  it("checks an objective response, records the result, and advances", () => {
    const onCheck = vi.fn();
    render(<ExerciseHarness onCheck={onCheck} />);

    expect(screen.getByText("Activity 1 of 2")).toBeInTheDocument();
    expect(screen.getByRole("progressbar", { name: "Activity 1 of 2" })).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText("Hello"));
    fireEvent.click(screen.getByRole("button", { name: "Check answer" }));

    expect(onCheck).toHaveBeenCalledWith("choose-greeting", "correct");
    expect(screen.getByText("Correct.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Next activity" }));

    expect(screen.getByText("Activity 2 of 2")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Say hello to a classmate." })).toHaveFocus();
  });

  it("allows retry without disclosing a supplied answer after an incorrect check", () => {
    render(<ExerciseHarness />);

    fireEvent.click(screen.getByLabelText("Yesterday"));
    fireEvent.click(screen.getByRole("button", { name: "Check answer" }));

    expect(screen.getByText("Not yet.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));

    expect(screen.getByRole("button", { name: "Check answer" })).toBeDisabled();
  });

  it("treats speaking as unscored self-practice and can restart after the final activity", () => {
    render(<ExerciseHarness />);

    fireEvent.click(screen.getByLabelText("Hello"));
    fireEvent.click(screen.getByRole("button", { name: "Check answer" }));
    fireEvent.click(screen.getByRole("button", { name: "Next activity" }));

    expect(screen.getByText(/not automatically scored/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Check answer" })).not.toBeInTheDocument();
    expect(screen.getByText("Use a greeting.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Finish practice" }));

    expect(screen.getByText("Practice set complete")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Restart practice" }));
    expect(screen.getByText("Activity 1 of 2")).toBeInTheDocument();
  });

  it("resumes a supplied exercise ID and safely falls back when it has changed", () => {
    const callbacks = {
      onCheck: () => {},
      onAdvance: () => {},
      onSelfPractice: () => {},
      onRestart: () => {},
    };
    const { rerender } = render(
      <ExerciseList
        exercises={exercises}
        runner={{ currentExerciseId: "say-hello", finished: false, exercises: {} }}
        {...callbacks}
      />,
    );
    expect(screen.getByText("Activity 2 of 2")).toBeInTheDocument();

    rerender(
      <ExerciseList
        exercises={exercises}
        runner={{ currentExerciseId: "removed-activity", finished: false, exercises: {} }}
        {...callbacks}
      />,
    );
    expect(screen.getByText("Activity 1 of 2")).toBeInTheDocument();
  });

  it("restores a saved objective result without retaining the learner response", () => {
    render(
      <ExerciseList
        exercises={exercises}
        runner={{
          currentExerciseId: "choose-greeting",
          finished: false,
          exercises: { "choose-greeting": { lastResult: "incorrect", completed: false } },
        }}
        onCheck={() => {}}
        onAdvance={() => {}}
        onSelfPractice={() => {}}
        onRestart={() => {}}
      />,
    );

    expect(screen.getByText("Not yet.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
    expect(screen.queryByDisplayValue("Yesterday")).not.toBeInTheDocument();
  });

  it("renders an unavailable state rather than treating unknown types as self-practice", () => {
    render(
      <ExerciseList
        exercises={[{ id: "unsupported", type: "translation", prompt: "Translate this." }]}
        onCheck={() => {}}
        onAdvance={() => {}}
        onSelfPractice={() => {}}
        onRestart={() => {}}
      />,
    );
    expect(screen.getByText("This activity is not available in the current learner interface.")).toBeInTheDocument();
  });

  it("runs every implemented objective exercise shape with supplied answer data", () => {
    const onCheck = vi.fn();
    const callbacks = {
      onCheck,
      onAdvance: () => {},
      onSelfPractice: () => {},
      onRestart: () => {},
    };
    const { rerender } = render(
      <ExerciseList
        exercises={[{ id: "blank", type: "fill_blank", prompt: "Type hello.", correct_answer: "hello" }]}
        {...callbacks}
      />,
    );
    fireEvent.change(screen.getByLabelText("Your answer"), { target: { value: "hello" } });
    fireEvent.click(screen.getByRole("button", { name: "Check answer" }));
    expect(onCheck).toHaveBeenLastCalledWith("blank", "correct");

    rerender(
      <ExerciseList
        exercises={[{ id: "match", type: "matching", prompt: "Match.", pairs: [{ left: "one", right: "eins" }] }]}
        {...callbacks}
      />,
    );
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "eins" } });
    fireEvent.click(screen.getByRole("button", { name: "Check answer" }));
    expect(onCheck).toHaveBeenLastCalledWith("match", "correct");

    rerender(
      <ExerciseList
        exercises={[{ id: "order", type: "ordering", prompt: "Order.", items: ["second", "first"], correct_order: ["first", "second"] }]}
        {...callbacks}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Move first up" }));
    fireEvent.click(screen.getByRole("button", { name: "Check answer" }));
    expect(onCheck).toHaveBeenLastCalledWith("order", "correct");

    for (const type of ["reading", "listening"] as const) {
      rerender(
        <ExerciseList
          exercises={[{ id: type, type, prompt: `${type} question.`, questions: [{ question: "Who?", acceptable_answers: ["Lan"] }] }]}
          {...callbacks}
        />,
      );
      fireEvent.change(screen.getByLabelText("Who?"), { target: { value: "Lan" } });
      fireEvent.click(screen.getByRole("button", { name: "Check answer" }));
      expect(onCheck).toHaveBeenLastCalledWith(type, "correct");
    }
  });

  it("renders selection and completion as objective text answers and writing as self-practice", () => {
    const callbacks = { onCheck: vi.fn(), onAdvance: () => {}, onSelfPractice: vi.fn(), onRestart: () => {} };
    const { rerender } = render(
      <ExerciseList exercises={[{ id: "selection", type: "selection", prompt: "Select.", answer: "yes" }]} {...callbacks} />,
    );
    fireEvent.change(screen.getByLabelText("Your answer"), { target: { value: "yes" } });
    fireEvent.click(screen.getByRole("button", { name: "Check answer" }));
    expect(callbacks.onCheck).toHaveBeenCalledWith("selection", "correct");

    rerender(<ExerciseList exercises={[{ id: "completion", type: "completion", prompt: "Complete.", answer: "done" }]} {...callbacks} />);
    fireEvent.change(screen.getByLabelText("Your answer"), { target: { value: "done" } });
    fireEvent.click(screen.getByRole("button", { name: "Check answer" }));
    expect(callbacks.onCheck).toHaveBeenCalledWith("completion", "correct");

    rerender(<ExerciseList exercises={[{ id: "writing", type: "writing", prompt: "Write.", rubric: "Use complete sentences." }]} {...callbacks} />);
    expect(screen.getByText(/not automatically scored/i)).toBeInTheDocument();
  });
});
