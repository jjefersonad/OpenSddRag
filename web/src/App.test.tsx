import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import App from "./App";

describe("App", () => {
  it("renders the layout shell brand", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <Routes>
          <Route path="/" element={<App />} />
        </Routes>
      </MemoryRouter>,
    );
    expect(screen.getByText("OpenSddRag")).toBeInTheDocument();
  });
});
