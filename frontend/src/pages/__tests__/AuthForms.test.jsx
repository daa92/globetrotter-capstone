// frontend/src/pages/__tests__/AuthForms.test.jsx
//
// Actually renders <Register /> and <Login /> in jsdom and drives them
// exactly like a user would (fill fields, click submit) against a REAL
// running backend — unlike scripts/verify_auth_flow.mjs, which only ever
// calls fetch() directly and never executes a single line of React.
// This is what catches things a pure-fetch simulation can't: a broken
// import, a hook bug, a form field not actually wired to its handler, a
// <label> not associated with its <input> (which this test suite is what
// caught, in fact — every form's labels were missing htmlFor/id pairs
// before this test existed).
//
// Run with the backend live on :8000:
//   npm run test:auth-forms
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom/vitest";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import "../../i18n"; // same side-effect import main.jsx does — without this, t() returns raw keys
import { AuthProvider } from "../../context/AuthContext";
import Register from "../Register";
import Login from "../Login";

function renderWithProviders(ui) {
  return render(<MemoryRouter><AuthProvider>{ui}</AuthProvider></MemoryRouter>);
}

describe("Register page, rendered for real in jsdom, against the real backend", () => {
  it("lets a user actually fill the form and submit it", async () => {
    const user = userEvent.setup();
    renderWithProviders(<Register />);

    const username = `jsdom_${Date.now()}`;

    await user.type(screen.getByLabelText(/username/i), username);
    await user.type(screen.getByLabelText(/^email$/i), `${username}@example.com`);
    await user.type(screen.getByLabelText(/^password$/i), "JsdomPass123");
    await user.type(screen.getByLabelText(/confirm password/i), "JsdomPass123");

    await user.click(screen.getByRole("button", { name: /sign up|register/i }));

    await waitFor(() => {
      expect(screen.getByText(/verify your account/i)).toBeInTheDocument();
    }, { timeout: 8000 });
  });
});

describe("Login page, rendered for real in jsdom, against the real backend", () => {
  it("shows a clear error for wrong credentials (proves the submit handler actually fires)", async () => {
    const user = userEvent.setup();
    renderWithProviders(<Login />);

    await user.type(screen.getByLabelText(/username/i), "definitely_not_a_real_user");
    await user.type(screen.getByLabelText(/password/i), "wrongpassword1");
    await user.click(screen.getByRole("button", { name: /log in/i }));

    await waitFor(() => {
      expect(screen.getByText(/invalid username or password/i)).toBeInTheDocument();
    }, { timeout: 8000 });
  });
});
