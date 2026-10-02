import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router-dom";
import { router } from "./routes";

const container = document.getElementById("root");
if (container) {
  createRoot(container).render(<RouterProvider router={router} />);
}
