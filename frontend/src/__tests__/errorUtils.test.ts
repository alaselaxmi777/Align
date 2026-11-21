import { describe, it, expect } from "vitest";
import { formatApiError } from "../lib/errorUtils";

describe("formatApiError", () => {
  it("formats Pydantic 422 array of validation details into human sentences", () => {
    const pydantic422 = {
      detail: [
        {
          type: "string_too_short",
          loc: ["body", "description"],
          msg: "String should have at least 10 characters",
          input: "Too short",
        },
        {
          type: "value_error",
          loc: ["body", "github_repo_url"],
          msg: "Value error, URL must use http:// or https:// scheme",
          input: "bad-url",
        },
      ],
    };

    const formatted = formatApiError(pydantic422);
    expect(formatted).toBe(
      "Description: Must be at least 10 characters. GitHub Repository URL: URL must use http:// or https:// scheme"
    );
  });

  it("handles string detail", () => {
    expect(formatApiError({ detail: "User already exists" })).toBe("User already exists");
  });

  it("handles stringified JSON", () => {
    const raw = JSON.stringify({ detail: [{ loc: ["body", "title"], msg: "Field required" }] });
    expect(formatApiError(raw)).toBe("Title: This field is required");
  });

  it("handles Network errors", () => {
    expect(formatApiError(new Error("Failed to fetch"))).toBe(
      "Network connection error. Please check your internet connection."
    );
  });
});
