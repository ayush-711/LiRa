import { describe, expect, it } from "vitest";
import { dueState, formatBytes, initials, avatarColor, cn } from "./utils";

describe("dueState", () => {
  const iso = (offsetDays: number) => {
    const d = new Date();
    d.setDate(d.getDate() + offsetDays);
    return d.toISOString().slice(0, 10);
  };

  it("returns 'none' when there is no due date", () => {
    expect(dueState(null)).toBe("none");
  });

  it("trusts the server's overdue flag", () => {
    // The server owns overdue semantics (due < today AND not done); the UI must
    // not second-guess it, otherwise a Done-but-past-due issue looks overdue.
    expect(dueState(iso(-5), true)).toBe("overdue");
    expect(dueState(iso(-5), false)).toBe("overdue"); // past date, still overdue
  });

  it("recognises today and tomorrow", () => {
    expect(dueState(iso(0))).toBe("today");
    expect(dueState(iso(1))).toBe("tomorrow");
  });

  it("treats further-out dates as upcoming", () => {
    expect(dueState(iso(10))).toBe("upcoming");
  });
});

describe("initials", () => {
  it("takes the first letter of the first two words", () => {
    expect(initials("Priya Sharma")).toBe("PS");
    expect(initials("Ayush")).toBe("A");
  });

  it("ignores extra whitespace and extra names", () => {
    expect(initials("  Rahul   Kumar  Singh ")).toBe("RK");
  });
});

describe("avatarColor", () => {
  it("is deterministic for the same seed", () => {
    expect(avatarColor("priya@lira.local")).toBe(avatarColor("priya@lira.local"));
  });

  it("returns a hex colour", () => {
    expect(avatarColor("anyone")).toMatch(/^#[0-9a-f]{6}$/i);
  });
});

describe("formatBytes", () => {
  it("formats across units", () => {
    expect(formatBytes(512)).toBe("512 B");
    expect(formatBytes(2048)).toBe("2 KB");
    expect(formatBytes(5 * 1024 * 1024)).toBe("5.0 MB");
  });
});

describe("cn", () => {
  it("merges conflicting tailwind classes, last one winning", () => {
    expect(cn("p-2", "p-4")).toBe("p-4");
  });

  it("drops falsy values", () => {
    expect(cn("a", false && "b", undefined, "c")).toBe("a c");
  });
});
