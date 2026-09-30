import { describe, expect, it, vi } from "vitest";
import { useState } from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { MentionTextarea, handleFor } from "./MentionTextarea";
import type { User } from "@/lib/types";

const people: User[] = [
  { id: 1, name: "Priya Sharma", email: "priya@lira.local", avatar_url: null, role: "member", is_active: true },
  { id: 2, name: "Rahul Kumar", email: "rahul@lira.local", avatar_url: null, role: "member", is_active: true },
];

/** The component is controlled, so tests need real state to drive it. */
function Harness({ onChangeSpy }: { onChangeSpy?: (v: string) => void }) {
  const [value, setValue] = useState("");
  return (
    <MentionTextarea
      value={value}
      onChange={(v) => { setValue(v); onChangeSpy?.(v); }}
      people={people}
    />
  );
}

function type(text: string) {
  const box = screen.getByRole("textbox") as HTMLTextAreaElement;
  fireEvent.change(box, { target: { value: text } });
  // jsdom leaves the caret at the end after a programmatic change
  box.selectionStart = text.length;
  fireEvent.keyUp(box);
  return box;
}

describe("handleFor", () => {
  it("uses the email local-part, which is what the server matches on", () => {
    expect(handleFor(people[0])).toBe("priya");
  });
});

describe("MentionTextarea", () => {
  it("suggests matching people after typing @", () => {
    render(<Harness />);
    type("hey @pr");
    expect(screen.getByText("Priya Sharma")).toBeInTheDocument();
    expect(screen.queryByText("Rahul Kumar")).toBeNull();
  });

  it("does not suggest without an @ token", () => {
    render(<Harness />);
    type("just text");
    expect(screen.queryByText("Priya Sharma")).toBeNull();
  });

  it("inserts the resolvable handle when a suggestion is picked", () => {
    const spy = vi.fn();
    render(<Harness onChangeSpy={spy} />);
    type("hey @pr");
    fireEvent.mouseDown(screen.getByText("Priya Sharma"));
    expect(spy).toHaveBeenLastCalledWith("hey @priya ");
  });

  it("matches on display name too", () => {
    render(<Harness />);
    type("@kumar");
    expect(screen.getByText("Rahul Kumar")).toBeInTheDocument();
  });

  it("closes the suggestions on Escape", () => {
    render(<Harness />);
    const box = type("hey @pr");
    expect(screen.getByText("Priya Sharma")).toBeInTheDocument();
    fireEvent.keyDown(box, { key: "Escape" });
    expect(screen.queryByText("Priya Sharma")).toBeNull();
  });
});
