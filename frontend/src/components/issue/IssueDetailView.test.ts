import { describe, expect, it } from "vitest";
import { issueDetailInvalidateQueryKeys } from "./IssueDetailView";

describe("issueDetailInvalidateQueryKeys", () => {
  it("includes activity invalidation for the current issue", () => {
    expect(issueDetailInvalidateQueryKeys("DOC-123")).toEqual([
      ["issue", "DOC-123"],
      ["activity", "DOC-123"],
      ["board"],
      ["issues"],
      ["my-issues"],
    ]);
  });
});
