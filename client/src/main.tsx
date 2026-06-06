import "./styles/custom.scss";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { DbProvider } from "./db/DbContext";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <DbProvider>
        <App />
      </DbProvider>
    </BrowserRouter>
  </StrictMode>,
);
