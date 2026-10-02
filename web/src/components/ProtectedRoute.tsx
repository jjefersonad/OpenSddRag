import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { getToken } from "../api/client";

/** Route guard (REQ-008): redirect to /login when no token is stored,
 *  without fetching any data. */
export default function ProtectedRoute({ children }: { children: ReactNode }) {
  if (!getToken()) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}
