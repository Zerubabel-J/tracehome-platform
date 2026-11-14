import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router";
import { AuthProvider } from "./auth";
import { Layout } from "./components/Layout";
import { AdvertiserPage } from "./pages/AdvertiserPage";
import { ListingPage } from "./pages/ListingPage";
import { SearchPage } from "./pages/SearchPage";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<SearchPage />} />
            <Route path="listings/:id" element={<ListingPage />} />
            <Route path="advertiser" element={<AdvertiserPage />} />
            <Route path="*" element={<p>Page not found.</p>} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  </StrictMode>,
);
