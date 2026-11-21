/**
 * Universal error parser for ALIGN API responses, FastAPI 422 validation details,
 * network errors, and unexpected exceptions.
 */

interface PydanticErrorDetail {
  loc?: (string | number)[];
  msg?: string;
  type?: string;
  ctx?: Record<string, any>;
}

/**
 * Converts a technical field path like ["body", "github_repo_url"] into a clean label
 */
function formatFieldLabel(loc?: (string | number)[]): string {
  if (!loc || loc.length === 0) return "";
  const field = String(loc[loc.length - 1]);
  if (field === "body" || field === "query") return "";

  const knownLabels: Record<string, string> = {
    title: "Title",
    tagline: "Tagline",
    description: "Description",
    category: "Category",
    stage: "Stage",
    required_roles: "Roles Needed",
    skills_needed: "Skills Needed",
    github_repo_url: "GitHub Repository URL",
    live_demo_url: "Live Demo URL",
    email: "Email",
    password: "Password",
    username: "Username",
    name: "Name",
    file: "Video/File",
  };

  if (knownLabels[field]) return knownLabels[field];

  // Convert snake_case to Title Case
  return field
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

/**
 * Cleans technical validation messages like "Value error, URL must use..."
 */
function cleanMessage(msg: string): string {
  let cleaned = msg.replace(/^Value error,\s*/i, "");
  cleaned = cleaned.replace(/^String should have at least\s*/i, "Must be at least ");
  cleaned = cleaned.replace(/^String should have at most\s*/i, "Must be at most ");
  cleaned = cleaned.replace(/^Field required/i, "This field is required");
  return cleaned;
}

/**
 * Formats any error (string, Error, FastAPI 422 object/array, network failure) into
 * clean, user-friendly sentences.
 */
export function formatApiError(error: unknown, fallbackMessage: string = "An unexpected error occurred."): string {
  if (!error) return fallbackMessage;

  // 1. Primitive string
  if (typeof error === "string") {
    if (error.trim().startsWith("{") || error.trim().startsWith("[")) {
      try {
        const parsed = JSON.parse(error);
        return formatApiError(parsed, fallbackMessage);
      } catch {
        return error;
      }
    }
    return error;
  }

  // 2. Error object
  if (error instanceof Error) {
    if (error.message.includes("Failed to fetch") || error.message.includes("NetworkError")) {
      return "Network connection error. Please check your internet connection.";
    }
    if (error.message.startsWith("{") || error.message.startsWith("[")) {
      try {
        const parsed = JSON.parse(error.message);
        return formatApiError(parsed, fallbackMessage);
      } catch {
        return error.message;
      }
    }
    return error.message;
  }

  // 3. Object containing `detail`
  if (typeof error === "object" && error !== null) {
    const errObj = error as Record<string, any>;

    // FastAPI 422 validation array: { detail: [ { loc: [...], msg: "..." } ] }
    if (Array.isArray(errObj.detail) && errObj.detail.length > 0) {
      const messages = errObj.detail.map((d: PydanticErrorDetail) => {
        const field = formatFieldLabel(d.loc);
        const text = cleanMessage(d.msg || "Invalid value");
        if (field) {
          return `${field}: ${text}`;
        }
        return text;
      });
      return messages.join(". ");
    }

    // Direct string detail: { detail: "User with this email already exists" }
    if (typeof errObj.detail === "string" && errObj.detail.trim().length > 0) {
      return errObj.detail;
    }

    // Direct message property
    if (typeof errObj.message === "string" && errObj.message.trim().length > 0) {
      return errObj.message;
    }

    // Array at top level
    if (Array.isArray(error) && error.length > 0) {
      const messages = (error as PydanticErrorDetail[]).map((d) => {
        const field = formatFieldLabel(d.loc);
        const text = cleanMessage(d.msg || "Invalid value");
        return field ? `${field}: ${text}` : text;
      });
      return messages.join(". ");
    }
  }

  return fallbackMessage;
}
