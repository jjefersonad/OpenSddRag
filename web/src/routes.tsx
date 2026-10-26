import { createBrowserRouter, Navigate, type RouteObject } from "react-router-dom";
import App from "./App";
import LoginPage from "./features/auth/LoginPage";
import Dashboard from "./features/projects/Dashboard";
import DocsPage from "./features/docs/DocsPage";
import KeysPage from "./features/keys/KeysPage";
import LandingPage from "./features/landing/LandingPage";
import ProjectDetail from "./features/projects/ProjectDetail";
import ProtectedRoute from "./components/ProtectedRoute";

/**
 * Route table (design D1 — web-ui-design-alignment REQ-002).
 *   /           public landing
 *   /login      public
 *   /docs       public
 *   /projects   dashboard (protected)
 *   /keys       MCP API key management (protected)
 *   /p/:slug           project detail shell (protected)
 *   /p/:slug/c/:change change reader inside the same shell (web-change-reader D3)
 *   *                  → /
 */
export const routes: RouteObject[] = [
  { path: "/", element: <LandingPage /> },
  { path: "/login", element: <LoginPage /> },
  { path: "/docs", element: <DocsPage /> },
  {
    path: "/projects",
    element: (
      <ProtectedRoute>
        <App />
      </ProtectedRoute>
    ),
    children: [{ index: true, element: <Dashboard /> }],
  },
  {
    path: "/keys",
    element: (
      <ProtectedRoute>
        <App />
      </ProtectedRoute>
    ),
    children: [{ index: true, element: <KeysPage /> }],
  },
  {
    path: "/p/:slug",
    element: (
      <ProtectedRoute>
        <App />
      </ProtectedRoute>
    ),
    children: [
      { index: true, element: <ProjectDetail /> },
      { path: "c/:change", element: <ProjectDetail /> },
    ],
  },
  { path: "*", element: <Navigate to="/" replace /> },
];

export const router = createBrowserRouter(routes);