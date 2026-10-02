import { createBrowserRouter, Navigate, type RouteObject } from "react-router-dom";
import App from "./App";
import ProtectedRoute from "./components/ProtectedRoute";
import LoginPage from "./features/auth/LoginPage";
import Dashboard from "./features/projects/Dashboard";
import DocsPage from "./features/docs/DocsPage";
import ProjectDetail from "./features/projects/ProjectDetail";

/**
 * Route table (design D2). Exported separately so tests can build a
 * memory router from the same definitions.
 *   /login      public
 *   /           dashboard (protected)
 *   /p/:slug    project detail shell (protected)
 *   /docs       design-system reference (protected)
 *   *           → /
 */
export const routes: RouteObject[] = [
  { path: "/login", element: <LoginPage /> },
  {
    path: "/",
    element: (
      <ProtectedRoute>
        <App />
      </ProtectedRoute>
    ),
    children: [
      { index: true, element: <Dashboard /> },
      { path: "p/:slug", element: <ProjectDetail /> },
      { path: "docs", element: <DocsPage /> },
    ],
  },
  { path: "*", element: <Navigate to="/" replace /> },
];

export const router = createBrowserRouter(routes);
