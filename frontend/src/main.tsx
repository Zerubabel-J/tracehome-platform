import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Link, Navigate, Route, Routes } from "react-router";
import { AuthProvider } from "./auth";
import { Layout } from "./components/Layout";
import { ContactsPage } from "./pages/ContactsPage";
import { DemoPage } from "./pages/DemoPage";
import { ListingPage } from "./pages/ListingPage";
import { ModerationPage } from "./pages/ModerationPage";
import { SearchPage } from "./pages/SearchPage";
import { WorkspacePage } from "./pages/WorkspacePage";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<SearchPage />} />
            <Route path="listings/:id" element={<ListingPage />} />
            <Route path="demo" element={<DemoPage />} />
            <Route path="contacts" element={<ContactsPage />} />
            <Route path="workspace" element={<WorkspacePage />} />
            <Route path="advertiser" element={<Navigate to="/workspace" replace />} />
            <Route path="moderation" element={<ModerationPage />} />
            <Route
              path="*"
              element={
                <div className="gate">
                  <h1>Page not found</h1>
                  <Link to="/" className="btn">
                    Back to search
                  </Link>
                </div>
              }
            />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  </StrictMode>,
);
