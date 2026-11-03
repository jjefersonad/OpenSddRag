import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router-dom";
import { router } from "./routes";
import "./styles/base.css"; // global tokens + reset — imported at the entry so public routes (landing, login, docs) get it too (REQ-017)

const container = document.getElementById("root");
if (container) {
  createRoot(container).render(<RouterProvider router={router} />);
}
