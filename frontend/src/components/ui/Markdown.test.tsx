import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Markdown } from "./Markdown";

describe("Markdown", () => {
  it("renders formatting rather than raw syntax", () => {
    render(<Markdown>{"**bold** and `code`"}</Markdown>);
    expect(screen.getByText("bold").tagName).toBe("STRONG");
    expect(screen.getByText("code").tagName).toBe("CODE");
    // The raw markers must not leak into the output.
    expect(screen.queryByText(/\*\*bold\*\*/)).toBeNull();
  });

  it("renders lists and headings", () => {
    render(<Markdown>{"# Title\n\n- one\n- two"}</Markdown>);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Title");
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
  });

  it("does not execute embedded HTML (XSS guard)", () => {
    const { container } = render(
      <Markdown>{'<img src=x onerror="alert(1)"> <script>alert(2)</script>'}</Markdown>
    );
    // raw HTML is escaped, not parsed into live elements
    expect(container.querySelector("script")).toBeNull();
    expect(container.querySelector("img")).toBeNull();
  });

  it("opens links safely in a new tab", () => {
    render(<Markdown>{"[docs](https://example.com)"}</Markdown>);
    const link = screen.getByRole("link", { name: "docs" });
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", expect.stringContaining("noopener"));
  });
});
