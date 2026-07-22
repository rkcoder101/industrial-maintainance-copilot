import { render, screen } from "@testing-library/react";
import React from "react";
import { describe, expect, it } from "vitest";

import { StatusBadge } from "@/app/status-badge";

describe("StatusBadge", () => {
  it("renders a human-readable status", () => {
    render(<StatusBadge status="ok" />);

    expect(screen.getByText("Online")).toBeInTheDocument();
  });
});
